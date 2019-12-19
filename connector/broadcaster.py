import time, datetime

from .models import Meeting, User
from django.utils.timezone import make_aware

from django.db.models import Q


def broadacst_meeting_details(cb, year, week):
    participants_id = Meeting.get_participants_id(year=year, week=week)

    if len(participants_id) > 0:
        for p_id in participants_id:
            participant_partners_id = set()

            participant_meetings = Meeting.objects.filter(Q(user_a_telegram_id=p_id) | Q(user_b_telegram_id=p_id))

            for m in participant_meetings:
                if m.user_a_telegram_id != p_id:
                    participant_partners_id.add(m.user_a_telegram_id)
                if m.user_b_telegram_id != p_id:
                    participant_partners_id.add(m.user_b_telegram_id)

            participant_partners_id = list(participant_partners_id)
            total_partners = len(participant_partners_id)

            p = User.objects.get(telegram_id=p_id)

            message = "Привет, {user_name}!\n\n".format(user_name=p.first_name) + \
                      "Идет новая неделя Random Coffee!\n\n" + \
                      "Мы запланировали тебе {meetings_counter} на этой неделе:\n\n" \
                          .format(
                          meetings_counter="%d %s" % (total_partners,
                                                      "встречу" if total_partners == 1 else
                                                      "встречи" if total_partners < 5 else "встреч")
                      )

            for pp_id in participant_partners_id:
                pp = User.objects.get(telegram_id=pp_id)

                he_or_she = 'он' if pp.gender == 'M' else 'она'
                his_or_her = 'его' if pp.gender == 'M' else 'её'
                him_or_her = 'ним' if pp.gender == 'M' else 'ней'
                ending_verb = '' if pp.gender == 'M' else 'а'

                message += "{partner_name}\n{phone_number}\n{job}\n{about}\n" \
                    .format(
                    partner_name="<i>%s</i>" % (pp.full_name),
                    phone_number="%s номер телефона: <b>%s</b>" % (his_or_her.capitalize(), pp.phone_number),
                    job='В коворкинге %s работает без коллег' % (he_or_she) if pp.group_name == '' else
                    'В коворкинге %s работает в компании: <i>%s</i>' % (he_or_she, pp.group_name),
                    about='Вот что %s пишет о себе: <i>%s</i>\n' % (he_or_she, pp.about) if pp.about != '' else
                    'К сожалению, %s ничего о себе не написал%s\n' % (he_or_she, ending_verb)
                )

            message += 'Спишись с {him_or_her} поскорее, пока неделя еще не расписана.\n\nУдачи!' \
                .format(
                him_or_her=him_or_her if total_partners == 1 else "ними"
            )

            dialog = cb.get_dialog(user=p)

            now = make_aware(datetime.datetime.now())

            message = dialog.send_message(text=message)

            for m in Meeting.objects.filter(user_a_telegram_id=p_id):
                m.broadcasted_at = now
                m.save()

            for m in Meeting.objects.filter(user_b_telegram_id=p_id):
                m.broadcasted_at = now
                m.save()

            time.sleep(2)
    else:
        print("No meetings are scheduled for this week: year=%d, week=%d" % (year, week))

    return
