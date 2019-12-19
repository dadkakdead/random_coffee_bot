import time

from django.core.management.base import BaseCommand

from connector.apps import ChatbotConnector
from connector.chatbot import *
from connector.models import User


class Command(BaseCommand):
    help = "Send invitations to all the registered users " \
           "(by default, invitations are sent for next week from day or running script)"

    def add_arguments(self, parser):
        parser.add_argument('--token', '-t', help="Bot token", default=None)
        parser.add_argument('--username', '-u', help="Bot username", default=None)

        parser.add_argument('--year', '-y', type=int, help="Invination year (ISO calendar)", default=None)
        parser.add_argument('--week', '-w', type=int, help="Invination year (ISO calendar)", default=None)

    def handle(self, *args, **options):
        cb = ChatbotConnector.get_bot(options.get('token'), options.get('username'))

        if not cb:
            self.stderr.write("Bot not found")
            return

        registered_users = [u for u in User.objects.all() if (u.finished_registration is True) and (u.enabled is True)]

        if options.get('year') is None or options.get('week') is None:
            year, week = Clock.get_next_iso_week()
        else:
            year = options.get('year')
            week = options.get('week')

        for u in registered_users:
            try:
                inv = Invitation.objects.get(
                    user=u,
                    year=year,
                    week=week
                )
                inv.reset_decision()
                inv.rearrange_meeetings()
            except ObjectDoesNotExist:
                pass

            dialog = cb.get_dialog(user=u)

            dialog.transition_to(ReplyToMeetingInvitationState(params={"year": year, "week": week}))

            time.sleep(2)


