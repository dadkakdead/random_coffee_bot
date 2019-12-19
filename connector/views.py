import json
import datetime, time

from django.shortcuts import render
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from django.conf import settings


from .models import User, Invitation, Meeting
from .clock import Clock

import telegram
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
import logging
logger = logging.getLogger(__name__)

from .apps import ChatbotConnector
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden

from .chatbot import ReplyToMeetingInvitationState, CollectMeetingFeedbackState

from .broadcaster import broadacst_meeting_details

@csrf_exempt
def webhook (request, bot_token):
    logger.info(bot_token)
    bot = ChatbotConnector.get_bot(token=bot_token)
    if bot is None:
        logger.warn('Could not find bot for given token: {}'.format(bot_token))
        return JsonResponse({})

    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        logger.warn('Telegram bot <{}> receive invalid request : {}'.format(bot.username, repr(request)))
        return JsonResponse({})

    dispatcher = bot.updater.dispatcher
    if dispatcher is None:
        logger.error('Dispatcher for bot <{}> not found : {}'.format(bot.username, bot_token))
        return JsonResponse({})

    try:
        update = telegram.Update.de_json(data, bot)
        dispatcher.process_update(update)
        logger.debug('Bot <{}> : Processed update {}'.format(bot.username, update))
    except TelegramError as te:
        logger.warn("Bot <{}> : Error was raised while processing Update.".format(bot.username))
        dispatcher.dispatchError(update, te)

    except:
        logger.error("Bot <{}> : An uncaught error was raised while processing an update\n{}".format(bot.username, sys.exc_info()[0]))

    finally:
        return JsonResponse({})


@login_required
def schedule(request):
    try:
        year = int(request.GET.get('year'))
        week = int(request.GET.get('week'))
    except Exception as e:
        year, week = Clock.get_next_iso_week()

    year_week_ago, week_week_ago = Clock.get_previous_week_by_year_and_week(year, week)
    year_week_after, week_week_after = Clock.get_next_week_by_year_and_week(year, week)

    timestamps = {
        "week_ago": {
            "week": week_week_ago,
            "year": year_week_ago
        },
        "now": {
            "week": week,
            "year": year,
            "day_from": Clock.get_monday_same_week_by_year_and_week(year, week),
            "day_to": Clock.get_monday_same_week_by_year_and_week(year, week) + datetime.timedelta(days=7-1),
        },
        "week_after": {
            "week": week_week_after,
            "year": year_week_after
        }
    }

    users = User.objects.all()

    invitatons = Invitation.objects.filter(year=year, week=week)
    invited_users_id = list(map(lambda x: x.user.telegram_id, invitatons))

    user_funnel = {
        'accepted': [],
        'thinking': [],
        'declined': [],
        'awaiting_invitation': [],
        'awaiting_registration': [],
        'disabled': [],
        'undefined': []
    }

    for u in users:
        funnel_stage = 'undefined'
        if u.enabled:
            if u.finished_registration:
                if u.telegram_id in invited_users_id:
                    if invitatons.get(user=u).accepted is None:
                        funnel_stage = 'thinking'
                    elif invitatons.get(user=u).accepted:
                        funnel_stage = 'accepted'
                    elif not invitatons.get(user=u).accepted:
                        funnel_stage = 'declined'
                else:
                    funnel_stage = 'awaiting_invitation'
            else:
                funnel_stage = 'awaiting_registration'
        else:
            funnel_stage = 'disabled'

        user_funnel[funnel_stage].append(u.as_tuple())

    meetings_queryset = Meeting.objects.filter(year=year, week=week)
    meetings = []
    for m in meetings_queryset:
        user_a = User.objects.get(telegram_id=m.user_a_telegram_id)
        user_b = User.objects.get(telegram_id=m.user_b_telegram_id)
        meetings.append([user_a.as_tuple(), user_b.as_tuple(), m.meeting_took_place_aggregated, m.meeting_was_ok_aggregated])

    meeting_details_broadcasted = Meeting.were_details_broadcasted(year, week)

    return render(request, 'schedule.html', {
        'total_users': users.count(),
        "timestamps": timestamps,
        "users": user_funnel,
        "statistics": User.statistics(),
        "meetings": meetings,
        "meeting_details_broadcasted": meeting_details_broadcasted
    })


@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, ))
def shuffle_meetings(request):
    if request.method == 'POST':
        try:
            year = int(request.data['year'])
            week = int(request.data['week'])
            ignore_time_flow = request.data['ignore_time_flow']
        except Exception as e:
            return HttpResponseBadRequest()

    if request.method == 'GET':
        try:
            year = int(request.query_params['year'])
            week = int(request.query_params['week'])
            ignore_time_flow = request.query_params['ignore_time_flow']
        except Exception as e:
            return HttpResponseBadRequest()

    monday_requested_week = Clock.get_monday_same_week_by_year_and_week(year=year, week=week)

    year_upcoming, week_upcoming = Clock.get_next_iso_week()
    monday_upcoming_week = Clock.get_monday_same_week_by_year_and_week(year=year_upcoming, week=week_upcoming)

    if monday_requested_week >= monday_upcoming_week or ignore_time_flow:
        meetings_obj = Invitation.rearrange_meeetings(year=year, week=week)
        logger.info(meetings_obj)

        return JsonResponse(meetings_obj, status=200)
    else:
        return HttpResponseForbidden()


@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, ))
def resend_invitation(request):
    if request.method == 'POST':
        try:
            user_id = str(request.data['user_telegram_id'])
            year = int(request.data['year'])
            week = int(request.data['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    if request.method == 'GET':
        try:
            user_id = str(request.query_params['user_telegram_id'])
            year = int(request.query_params['year'])
            week = int(request.query_params['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    # assuming there is only one token in BOTS[] list
    cb = ChatbotConnector.get_bot(token=settings.RANDOM_COFFEE_PLATFORM.get('BOTS', [])[0]['TOKEN'])

    try:
        u = User.objects.get(telegram_id=user_id)

        if Invitation.objects.filter(user=u, year=year, week=week).count() > 0:
            inv = Invitation.objects.get(
                user=u,
                year=year,
                week=week,
            )
            inv.reset_decision()
            # need to rearrange because we now user's decision is undefined
            meetings_obj = inv.trigger_rearrange_meetings()
            logger.info(meetings_obj)

        dialog = cb.get_dialog(user=u)

        dialog.transition_to(ReplyToMeetingInvitationState(params={"year": year, "week": week}))

        #TODO: return some data about sent invitation
        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(e)
        print(e)
        return HttpResponseBadRequest()

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, ))
def connect_participants(request):
    if request.method == 'POST':
        try:
            year = int(request.data['year'])
            week = int(request.data['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    if request.method == 'GET':
        try:
            year = int(request.query_params['year'])
            week = int(request.query_params['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    # assuming there is only one token in BOTS[] list
    cb = ChatbotConnector.get_bot(token=settings.RANDOM_COFFEE_PLATFORM.get('BOTS', [])[0]['TOKEN'])

    try:
        if not Meeting.were_details_broadcasted(year, week):
            broadacst_meeting_details(cb, year, week)

        #TODO: return some data about sent meeting details
        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(e)
        print(e)
        return HttpResponseBadRequest()


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)


@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, ))
def collect_feedback(request):
    if request.method == 'POST':
        try:
            user_1_telegram_id = str(request.data['user_1_telegram_id']),
            user_2_telegram_id = str(request.data['user_2_telegram_id']),
            year = int(request.data['year'])
            week = int(request.data['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    if request.method == 'GET':
        try:
            user_1_telegram_id = str(request.query_params['user_1_telegram_id']),
            user_2_telegram_id = str(request.query_params['user_2_telegram_id']),
            year = int(request.query_params['year'])
            week = int(request.query_params['week'])
        except Exception as e:
            print(e)
            return HttpResponseBadRequest()

    # assuming there is only one token in BOTS[] list
    cb = ChatbotConnector.get_bot(token=settings.RANDOM_COFFEE_PLATFORM.get('BOTS', [])[0]['TOKEN'])

    try:
        if Meeting.were_details_broadcasted(year, week):
            print(year)
            print(week)
            print(user_1_telegram_id[0])
            print(user_2_telegram_id[0])

            m = Meeting.get_instance_by_unique_parameters(year=year, week=week, user_1_telegram_id=user_1_telegram_id[0], user_2_telegram_id=user_2_telegram_id[0])

            for p_id in [user_1_telegram_id[0], user_2_telegram_id[0]]:
                m.reset_user_feedback(user_telegram_id=p_id)

                dialog = cb.get_dialog(user=User.objects.get(telegram_id=p_id))

                dialog.transition_to(CollectMeetingFeedbackState(params={
                    "partner_id": m.get_partner_id(p_id),
                    "year": year,
                    "week": week
                }))

                time.sleep(0.5)

        #TODO: return some data about sent meeting details
        return JsonResponse({}, status=200)
    except Exception as e:
        logger.error(e)
        print(e)
        return HttpResponseBadRequest()


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)

