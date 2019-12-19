from django.core.management.base import BaseCommand

from connector.apps import ChatbotConnector
from connector.clock import Clock
from connector.models import Meeting

from connector.broadcaster import broadacst_meeting_details

class Command(BaseCommand):
    help = "Connect participants with each other in the beginning of the week"

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

        if not Meeting.were_details_broadcasted(year, week):
            broadacst_meeting_details(cb, year, week)
