import datetime
from django.utils.timezone import make_aware


class Clock:
    @classmethod
    def get_iso_week(cls, dt):
        return dt.isocalendar()[0], dt.isocalendar()[1]

    @classmethod
    def get_current_iso_week(cls):
        now = make_aware(datetime.datetime.now())
        return cls.get_iso_week(now)

    @classmethod
    def get_previous_iso_week(cls):
        now = make_aware(datetime.datetime.now())
        now_2 = now - datetime.timedelta(days=7)
        return cls.get_iso_week(now_2)

    @classmethod
    def get_next_iso_week(cls):
        now = make_aware(datetime.datetime.now())
        now_2 = now + datetime.timedelta(days=7)
        return cls.get_iso_week(now_2)

    @classmethod
    def get_monday_same_week_by_year_and_week(cls, year, week):
        d = "%d-W%d-1" % (year, week)
        # why %G-W%V-%u? see https://stackoverflow.com/questions/17087314/get-date-from-week-number
        r = make_aware(datetime.datetime.strptime(d, "%G-W%V-%u"))
        return r

    @classmethod
    def get_monday_same_week_by_timestamp(cls, dt):
        year, week = Clock.get_iso_week(dt)
        return Clock.get_monday_same_week_by_year_and_week(year, week)

    @classmethod
    def get_previous_week_by_year_and_week(cls, year, week):
        mon_this_week = Clock.get_monday_same_week_by_year_and_week(year, week)
        mon_last_week = mon_this_week - datetime.timedelta(days=7)
        return Clock.get_iso_week(mon_last_week)

    @classmethod
    def get_next_week_by_year_and_week(cls, year, week):
        mon_this_week = Clock.get_monday_same_week_by_year_and_week(year, week)
        mon_next_week = mon_this_week + datetime.timedelta(days=7)
        return Clock.get_iso_week(mon_next_week)

    @classmethod
    def get_week_boundaries(cls, year, week):
        day_from = Clock.get_monday_same_week_by_year_and_week(year, week)
        day_to = Clock.get_monday_same_week_by_year_and_week(year, week) + datetime.timedelta(days=7 - 1)
        return day_from, day_to

    @classmethod
    def get_week_boundaries_readable(cls, year, week):
        day_from, day_to = Clock.get_week_boundaries(year, week)
        return "%s - %s" % (datetime.datetime.strftime(day_from,"%d.%m.%y"), datetime.datetime.strftime(day_to, "%d.%m.%y"))

