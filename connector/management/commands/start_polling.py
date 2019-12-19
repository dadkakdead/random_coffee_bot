import logging

from django.core.management.base import BaseCommand

from connector.apps import ChatbotConnector


class Command(BaseCommand):
    help = "Run telegram bot in polling mode"

    def add_arguments(self, parser):
        parser.add_argument('--token', '-t', help="Bot token", default=None)
        parser.add_argument('--username', '-u', help="Bot username", default=None)

    def handle(self, *args, **options):
        from django.conf import settings
        if settings.RANDOM_COFFEE_PLATFORM.get('MODE', 'WEBHOOK') == 'WEBHOOK':
            self.stderr.write("Update mode set to 'WEBHOOK', change to POLLING if you want to use polling update")
            return

        cb = ChatbotConnector.get_bot(options.get('token'), options.get('username'))

        if not cb:
            self.stderr.write("Bot not found")
            return

        # Enable Logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

        logger = logging.getLogger("apps")
        logger.setLevel(logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console)

        poll_interval = settings.RANDOM_COFFEE_PLATFORM.get('POLL_INTERVAL', 0.0)
        timeout = settings.RANDOM_COFFEE_PLATFORM.get('TIMEOUT', 10)
        clean = settings.RANDOM_COFFEE_PLATFORM.get('POLL_CLEAN', False)
        bootstrap_retries = settings.RANDOM_COFFEE_PLATFORM.get('POLL_BOOTSTRAP_RETRIES', 0)
        read_latency = settings.RANDOM_COFFEE_PLATFORM.get('POLL_READ_LATENCY', 2.)
        allowed_updates = settings.RANDOM_COFFEE_PLATFORM.get('ALLOWED_UPDATES', None)

        self.stdout.write("Run polling...")

        cb.updater.start_polling(
            poll_interval=poll_interval,
            timeout=timeout,
            clean=clean,
            bootstrap_retries=bootstrap_retries,
            read_latency=read_latency,
            allowed_updates=allowed_updates
        )

        self.stdout.write("The bot is started and runs until we press Ctrl-C on the command line.")

        cb.updater.idle()
