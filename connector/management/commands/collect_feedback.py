import time

from django.core.management.base import BaseCommand

from connector.apps import ChatbotConnector
from connector.chatbot import *
from connector.models import User, Meeting


class Command(BaseCommand):
    help = "Collect feedback from meeting participants"

    def add_arguments(self, parser):
        parser.add_argument('--token', '-t', help="Bot token", default=None)
        parser.add_argument('--username', '-u', help="Bot username", default=None)

        parser.add_argument('--year', '-y', type=int, help="Year of meeting week (ISO calendar)", default=None)
        parser.add_argument('--week', '-w', type=int, help="Week number of meeting week (ISO calendar)", default=None)

    def handle(self, *args, **options):
        cb = ChatbotConnector.get_bot(options.get('token'), options.get('username'))

        if not cb:
            self.stderr.write("Bot not found")
            return

        if options.get('year') is None or options.get('week') is None:
            year, week = Clock.get_current_iso_week()
        else:
            year = options.get('year')
            week = options.get('week')

        participants_id = Meeting.get_participants_id(year=year, week=week)

        if len(participants_id) > 0:
            for p_id in participants_id:
                m = Meeting.objects.filter(Q(user_a_telegram_id=p_id) | Q(user_b_telegram_id=p_id))[0]
                m.reset_user_feedback(user_telegram_id=p_id)

                dialog = cb.get_dialog(user=User.objects.get(telegram_id=p_id))

                dialog.transition_to(CollectMeetingFeedbackState(params={
                    "partner_id": m.get_partner_id(p_id),
                    "year": year,
                    "week": week
                }))

                time.sleep(2)
        else:
            print("No meetings are scheduled for this week: year=%d, week=%d" % (year, week))


