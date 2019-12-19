from django.db import models
import django.utils.timezone
from .clock import Clock

from django.core.exceptions import ObjectDoesNotExist

from .vars import *

import logging
logger = logging.getLogger('connector.apps')

from django.db.models import Q


class Group(models.Model):
    name = models.CharField(max_length=300, unique=True)

    created_at = models.DateTimeField(default=django.utils.timezone.now)
    updated_at = models.DateTimeField(default=django.utils.timezone.now)

    @property
    def number_of_people(self):
        return len(User.objects.filter(group=self))

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.created_at = django.utils.timezone.now()

        self.updated_at = django.utils.timezone.now()

        return super(Group, self).save(*args, **kwargs)


class User(models.Model):
    telegram_id = models.CharField(max_length=100, blank=False)

    #personal details
    gender = models.CharField(max_length=100, choices=GENDER_CHOICES, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=False)
    last_name = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=100, choices=USER_TYPE_CHOICES, null=True, blank=True)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.PROTECT)
    about = models.CharField(max_length=300, blank=True)

    #contact details
    telegram_username = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=100, blank=True)

    meeting_frequency = models.CharField(max_length=100, choices=MEETING_FREQUENCY_CHOICES, null=True, blank=True)
    meeting_motivation = models.CharField(max_length=100, choices=MOTITVATION_CHOICES, null=True, blank=True)

    enabled = models.BooleanField(default=True, blank=False)

    #timestamps for statistics
    first_time_visited_at = models.DateTimeField(default=django.utils.timezone.now)
    registered_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=django.utils.timezone.now)
    updated_at = models.DateTimeField(default=django.utils.timezone.now)

    def __str__(self):
        return "%s (%s)" % (self.full_name, self.phone_number)

    @classmethod
    def statistics(cls):
        return {
            'gender': {
                'male': cls.objects.filter(gender=MALE, registered_at__isnull=False).count(),
                'female': cls.objects.filter(gender=FEMALE, registered_at__isnull=False).count()
            },
            'frequency': {
                'high': cls.objects.filter(meeting_frequency=HIGH, registered_at__isnull=False).count(),
                'medium': cls.objects.filter(meeting_frequency=MEDIUM, registered_at__isnull=False).count(),
                'low': cls.objects.filter(meeting_frequency=LOW, registered_at__isnull=False).count()
            },
            'motivation': {
                'dating': cls.objects.filter(meeting_motivation=DATING, registered_at__isnull=False).count(),
                'networking': cls.objects.filter(meeting_motivation=NETWORKING, registered_at__isnull=False).count(),
                'fun': cls.objects.filter(meeting_motivation=HAVING_FUN, registered_at__isnull=False).count()
            }
        }

    def as_tuple(self):
        return (self.telegram_id, self.full_name, self.group_name, self.phone_number)

    @property
    def group_name(self):
        if self.group is None:
            return  ''
        else:
            return self.group.name

    @property
    def full_name(self):
        return str(("%s %s") % (self.first_name, self.last_name)).strip()

    @property
    def finished_registration(self):
        return not(self.registered_at is None)

    @property
    def invitation_this_week(self):
        year, week = Clock.get_current_iso_week()
        try:
            return Invitation.objects.get(user=self, year=year, week=week)
        except ObjectDoesNotExist:
            return None

    @property
    def invitation_last_week(self):
        year, week = Clock.get_previous_iso_week()
        try:
            return Invitation.objects.get(user=self, year=year, week=week)
        except ObjectDoesNotExist:
            return None

    @property
    def invitation_next_week(self):
        year, week = Clock.get_next_iso_week()
        try:
            return Invitation.objects.get(user=self, year=year, week=week)
        except ObjectDoesNotExist:
            return None

    def find_unrated_meeting(self, year=None, week=None):
        if year is None or week is None:
            return

        # true and false overhead because
        # django.core.exceptions.FieldError: Unsupported lookup 'is_null' for BooleanField or join on the field not permitted, perhaps you meant isnull?
        mm = Meeting.objects.filter(
            (Q(user_a_telegram_id=self.telegram_id) & ~Q(user_a_meeting_took_place=True) & ~Q(user_a_meeting_took_place=False)) |
            (Q(user_b_telegram_id=self.telegram_id) & ~Q(user_b_meeting_took_place=True) & ~Q(user_b_meeting_took_place=False))
        )

        if mm.count() > 0:
            return mm[0]
        else:
            return

    def check_in(self):
        self.last_seen_at = django.utils.timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        # _state is internal Django thing
        if self._state.adding:
            self.first_time_visited_at = django.utils.timezone.now()

        self.updated_at = django.utils.timezone.now()

        return super(User, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['telegram_id'], name='unique_registered_user')
        ]


class UserState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    context = models.CharField(max_length=500, default="{'state_name': 'NullState', 'params': {}}")
    updated_at = models.DateTimeField(default=django.utils.timezone.now)

    def save(self, *args, **kwargs):
        self.updated_at = django.utils.timezone.now()

        return super(UserState, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_state')
        ]


class Invitation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    week = models.IntegerField()
    year = models.IntegerField()

    accepted = models.BooleanField(null=True)
    cancel_reason = models.CharField(blank=True, default='', max_length=100, choices=CANCELLATION_REASON_CHOICES)

    message_id = models.CharField(null=True, max_length=100)
    counter = models.IntegerField(default=0)

    sent_at = models.DateTimeField(default=django.utils.timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    def reset_decision(self):
        self.accepted = None
        self.cancel_reason = ''
        self.save()

    def trigger_rearrange_meetings(self):
        return Invitation.rearrange_meeetings(year=self.year, week=self.week)

    @classmethod
    def rearrange_meeetings(cls, year=None, week=None):
        if year is None or week is None:
            raise Exception('year or week are undefined')
        if not Meeting.were_details_broadcasted(year=year, week=week):
            if Meeting.objects.filter(year=year, week=week).count() > 0:
                Meeting.objects.filter(year=year, week=week).delete()

            from .blender import arrange_meetings
            meetings_obj = arrange_meetings(year=year, week=week)

            if meetings_obj != {}:
                for m in meetings_obj['meetings']:
                    Meeting(
                        year=year,
                        week=week,
                        user_a_telegram_id=m[0],
                        user_b_telegram_id=m[1]
                    ).save()
                return meetings_obj
            else:
                logger.info("Couldnt make meetings to satisfy demand")
                return {}
        else:
            logger.info("Meetings details were already broadcasted")
            return {}

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'week', 'year'], name='unique_week_invitation')
        ]


class Meeting(models.Model):
    week = models.IntegerField(blank=False)
    year = models.IntegerField(blank=False)

    user_a_telegram_id = models.CharField(blank=False, max_length=100)
    user_b_telegram_id = models.CharField(blank=False, max_length=100)

    user_a_meeting_took_place = models.BooleanField(null=True)
    user_b_meeting_took_place = models.BooleanField(null=True)

    user_a_happy = models.BooleanField(null=True)
    user_b_happy = models.BooleanField(null=True)

    user_a_meeting_failure_reason = models.CharField(blank=True, default='', max_length=100, choices=ARRANGEMENT_FAILURE_REASONS)
    user_b_meeting_failure_reason = models.CharField(blank=True, default='', max_length=100, choices=ARRANGEMENT_FAILURE_REASONS)

    updated_at = models.DateTimeField(default=django.utils.timezone.now)
    broadcasted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=django.utils.timezone.now)

    @property
    def user_a(self):
        return User.objects.get(telegram_id=self.user_a_telegram_id)

    @property
    def user_b(self):
        return User.objects.get(telegram_id=self.user_b_telegram_id)

    @property
    def meeting_was_ok_aggregated(self):
        return self.user_a_happy or self.user_b_happy

    @property
    def meeting_took_place_aggregated(self):
        return self.user_a_meeting_took_place is True or self.user_b_meeting_took_place is True

    def __str__(self):
        return "%s, w%dy%d %s - %s" % (self.created_at.strftime("%d.%m.%Y"),
                                self.week,
                                self.year,
                                User.objects.get(telegram_id=self.user_a_telegram_id).full_name,
                                User.objects.get(telegram_id=self.user_b_telegram_id).full_name)

    def reset_user_feedback(self, user_telegram_id):
        if user_telegram_id == self.user_a_telegram_id:
            self.user_a_meeting_took_place = None
            self.user_a_happy = None
            self.user_a_meeting_failure_reason = ''
        if user_telegram_id == self.user_b_telegram_id:
            self.user_b_meeting_took_place = None
            self.user_b_happy = None
            self.user_b_meeting_failure_reason = ''
        self.save()

    # partner is another person from user with telegram_id=user_telegram_id
    def get_partner_id(self, user_telegram_id):
        if not user_telegram_id in [self.user_a_telegram_id, self.user_b_telegram_id]:
            raise Exception("user_telegram_id %s not found in the meeting" % user_telegram_id)
        if self.user_a_telegram_id == user_telegram_id:
            return self.user_b_telegram_id
        if self.user_b_telegram_id == user_telegram_id:
            return self.user_a_telegram_id

    @classmethod
    def were_details_broadcasted(cls, year, week):
        return Meeting.objects.filter(broadcasted_at__isnull=False).count() > 0

    @classmethod
    def get_participants_id(cls, year, week):
        unique_participants = set()

        participants = cls.objects.filter(year=year, week=week)
        for pp in participants:
            unique_participants.add(pp.user_a_telegram_id)
            unique_participants.add(pp.user_b_telegram_id)

        return list(unique_participants)

    @classmethod
    def get_participants(cls, year, week):
        return User.objects.filter(telegram_id__in=Meeting.get_participants_id(year, week))

    @classmethod
    def get_instance_by_unique_parameters(cls, year, week, user_1_telegram_id, user_2_telegram_id):
        mm = Meeting.objects.filter(
                Q(year=year) &
                Q(week=week) &
                (
                    (Q(user_a_telegram_id=user_1_telegram_id) &
                     Q(user_b_telegram_id=user_2_telegram_id))
                     |

                    (Q(user_b_telegram_id=user_1_telegram_id) &
                     Q(user_a_telegram_id=user_2_telegram_id))
                )
            )
        if mm.count() == 1:
            return mm[0]
        else:
            return None

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.created_at = django.utils.timezone.now()

        self.updated_at = django.utils.timezone.now()

        return super(Meeting, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['week', 'year', 'user_a_telegram_id', 'user_b_telegram_id'], name='unique_meeting')
        ]


class Feedback(models.Model):
    user = models.ForeignKey(User, blank=False, on_delete=models.CASCADE)
    positive = models.BooleanField(null=True)
    text = models.CharField(max_length=300)
    sent_at = models.DateTimeField(default=django.utils.timezone.now)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.sent_at = django.utils.timezone.now()

        return super(Feedback, self).save(*args, **kwargs)

class Message(models.Model):
    user = models.ForeignKey(User, blank=False, on_delete=models.CASCADE)
    direction = models.CharField(null=True, blank=True, max_length=100)
    text = models.CharField(null=True, blank=True, max_length=10000)
    message_id = models.CharField(null=True, max_length=100)
    sent_at = models.DateTimeField(default=django.utils.timezone.now)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.sent_at = django.utils.timezone.now()

        return super(Message, self).save(*args, **kwargs)
