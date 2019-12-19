import random

from .models import User, Invitation, Meeting
from .clock import Clock

from django.db.models import Q

import logging
logger = logging.getLogger('connector.apps')

def update_possible_partners(profiles_dict, history_dict, capacity_dict):
    possible_partners = {}
    for u_id in capacity_dict:
        possible_partners[u_id] = []
        for u_id_2 in capacity_dict:
            if (not u_id_2 == u_id) and (not u_id_2 in history_dict[u_id]) and \
                    (capacity_dict[u_id] > 0) and \
                    (capacity_dict[u_id_2] > 0) and \
                    (
                            (profiles_dict[u_id]['group_name'] == '' and profiles_dict[u_id_2]['group_name'] == '') or
                            (profiles_dict[u_id]['group_name'] != profiles_dict[u_id_2]['group_name'])
                    ) and \
                    (
                            (profiles_dict[u_id]['motivation'] != 'D') or \
                            (profiles_dict[u_id]['motivation'] == 'D' and profiles_dict[u_id]['gender'] != profiles_dict[u_id_2]['gender'])
                    ):
                possible_partners[u_id].append(u_id_2)
    return possible_partners


def arrange_meetings(year=None, week=None):
    if week is None or year is None:
        raise Exception("Error: WEEK or YEAR are not specified")

    participants = Invitation.objects.filter(week=week, year=year, accepted=True)

    if len(participants) == 0:
        return {}

    participants_id = list(map(lambda x: x.user.telegram_id, participants))

    participants_data = User.objects.filter(telegram_id__in=participants_id)

    profiles_dict = {}
    for p in participants_data:
        profiles_dict[p.telegram_id] = {
            'group_name': p.group_name,
            'gender': p.gender,
            'frequency': p.meeting_frequency,
            'motivation': p.meeting_motivation
        }

    history_dict = {}
    for p_id in participants_id:
        p_id_str = str(p_id)
        unique_participants = []

        # doing two lookups to cover all options
        # USER -> PARTICIPANT & PARTICIPANT -> USER
        participants_b = Meeting.objects.filter(Q(user_a_telegram_id=p_id_str) & (Q(user_a_meeting_took_place=True) | Q(user_b_meeting_took_place=True)))
        for pB in participants_b:
            unique_participants.append(pB.user_b_telegram_id)

        participants_a = Meeting.objects.filter(Q(user_b_telegram_id=p_id_str) & (Q(user_a_meeting_took_place=True) | Q(user_b_meeting_took_place=True)))
        for pA in participants_a:
            unique_participants.append(pA.user_a_telegram_id)

        history_dict[p_id_str] = list(set(unique_participants))

    import copy
    history_dict_initial = copy.deepcopy(history_dict)

    capacity_dict = {}

    year_last_week, week_last_week = Clock.get_previous_week_by_year_and_week(year, week)
    participants_previous_week = Meeting.get_participants_id(year=year_last_week, week=week_last_week)

    for p_id in participants_id:
        c = 1

        if profiles_dict[p_id]['frequency'] == 'H':
            c = 2
        if profiles_dict[p_id]['frequency'] == 'M':
            c = 1
        if profiles_dict[p_id]['frequency'] == 'L':
            if p_id in participants_previous_week:
                c = 0
            else:
                c = 1

        capacity_dict[p_id] = c

    import copy
    capacity_dict_initial = copy.deepcopy(capacity_dict)

    possible_partners_initial = update_possible_partners(profiles_dict, history_dict, capacity_dict)

    optimal_set_of_meetings = []
    min_participants_without_meeting = len(participants_id)
    min_participants_with_less_meetings_than_expected = len(participants_id)

    SHUFFLE_ITERATION = 5
    for it in range(0, SHUFFLE_ITERATION):
        meetings = []

        for u_id in participants_id:

            print(u_id)
            possible_partners = update_possible_partners(profiles_dict, history_dict, capacity_dict)
            print(possible_partners)

            if capacity_dict[u_id] > 0:
                if len(possible_partners[u_id]) == 0:
                    continue

                r = random.randint(0, len(possible_partners[u_id]) - 1)
                partner_id = possible_partners[u_id][r]

                meetings.append((u_id, partner_id))
                print((u_id, partner_id))
                history_dict[u_id].append(partner_id)
                history_dict[partner_id].append(u_id)
                capacity_dict[u_id] -= 1
                capacity_dict[partner_id] -= 1

        participants_without_meeting = list(filter(lambda x: capacity_dict[x] == capacity_dict_initial[x], capacity_dict))
        participants_with_less_meetings_than_expected = list(filter(lambda x: capacity_dict[x] > 0, capacity_dict))

        if len(participants_without_meeting) == 0 and len(participants_with_less_meetings_than_expected) == 0:
            optimal_set_of_meetings = meetings
            min_participants_without_meeting = 0
            min_participants_with_less_meetings_than_expected = 0
            break
        else:
            if len(participants_without_meeting) < min_participants_without_meeting:
                if len(participants_with_less_meetings_than_expected) < min_participants_with_less_meetings_than_expected:
                    optimal_set_of_meetings = meetings
                    min_participants_without_meeting = len(participants_without_meeting)
                    min_participants_with_less_meetings_than_expected = len(participants_with_less_meetings_than_expected)


    res = {
        'week': week,
        'year': year,
        'profiles': profiles_dict,
        'history': history_dict_initial,
        'capacity': capacity_dict_initial,
        'possible_partners': possible_partners_initial,
        'shuffle_iterations': SHUFFLE_ITERATION,
        'meetings': optimal_set_of_meetings,
        'left_alone': min_participants_without_meeting,
        'left_underutilized': min_participants_with_less_meetings_than_expected,
        'has_more_people_to_meet': len(list(filter(lambda k: len(possible_partners_initial[k]) > 0, possible_partners_initial.keys())))
    }

    print(res)

    return res



