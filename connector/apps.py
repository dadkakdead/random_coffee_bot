from django.apps import AppConfig
from django.apps import apps
from django.conf import settings
import importlib
import telegram
from django.utils.module_loading import module_has_submodule
from telegram.ext import Dispatcher
from telegram.ext import Updater
from telegram.error import InvalidToken, TelegramError

import os.path
import time

import logging
logger = logging.getLogger(__name__)


class ChatbotConnector(AppConfig):
    name = "connector"
    verbose_name = "Chatbot connector"

    __WEBHOOK_MODE, __POLLING_MODE = range(2)
    __modes = ['WEBHOOK', 'POLLING']

    # gets changed after ready() method is called first time
    ready_to_go = False

    bots = []

    @classmethod
    def get_bot(cls, token=None, username=None):
        logger.info("get_bot")
        logger.info(token)
        logger.info(username)
        logger.info(cls.bots)

        if username is None and token is None:
            return None

        if username:
            for b in cls.bots:
                if b.username == username:
                    return b

        if token:
            for b in cls.bots:
                logger.info(b.token)
                if b.token == token:
                    return b

        return None

    def ready(self):
        from .chatbot import Chatbot

        if self.ready_to_go:
            return
        self.ready_to_go = True

        self.mode = self.__WEBHOOK_MODE
        if settings.RANDOM_COFFEE_PLATFORM.get('MODE', 'WEBHOOK') == 'POLLING':
            self.mode = self.__POLLING_MODE

        #logger.info('Django Telegram Bot <{} mode>'.format(self.__modes[self.mode]))

        if self.mode == self.__WEBHOOK_MODE:
            webhook_site = settings.RANDOM_COFFEE_PLATFORM.get('WEBHOOK_SITE', None)
            if not webhook_site:
                logger.warn('Required WEBHOOK_SITE missing in settings')
                return
            if webhook_site.endswith("/"):
                webhook_site = webhook_site[:-1]

            cert_path = settings.RANDOM_COFFEE_PLATFORM.get('WEBHOOK_CERTIFICATE_PATH', None)
            if cert_path and os.path.exists(cert_path):
                logger.info('WEBHOOK_CERTIFICATE_PATH found in {}'.format(cert_path))
            else:
                logger.error('WEBHOOK_CERTIFICATE_PATH not found in {} '.format(cert_path))

        timeout = settings.RANDOM_COFFEE_PLATFORM.get('TIMEOUT', None)
        max_connections = settings.RANDOM_COFFEE_PLATFORM.get('WEBHOOK_MAX_CONNECTIONS', 40)
        allowed_updates = settings.RANDOM_COFFEE_PLATFORM.get('ALLOWED_UPDATES', None)
        request_kwargs = settings.RANDOM_COFFEE_PLATFORM.get('PROXY_REQUEST_KWARGS', None)

        #initialize bots
        b_counter = 0
        for b in settings.RANDOM_COFFEE_PLATFORM.get('BOTS', []):
            b_counter += 1
            token = b.get('TOKEN', None)
            print(token)
            if not token:
                break

            if self.mode == self.__WEBHOOK_MODE:
                try:
                    cb = Chatbot(community_name=b.get('COMMUNITY_NAME', ''), token=token)
                    cb.bot.delete_webhook()

                    cb.updater.start_webhook(listen='127.0.0.1',
                                              port=int(8081 + b_counter * 100),
                                              url_path=token)

                    cb.bot.set_webhook(url='{}/{}/'.format(webhook_site, token),
                                        certificate=open(cert_path, 'rb'),
                                        timeout=timeout,
                                        max_connections=max_connections,
                                        allowed_updates=allowed_updates)

                except InvalidToken:
                    logger.error('Invalid Token : {}'.format(token))
                    return

                except TelegramError as er:
                    logger.error('Error : {}'.format(er))
                    return

            if self.mode == self.__POLLING_MODE:
                try:
                    cb = Chatbot(community_name=b.get('COMMUNITY_NAME', 'Без названия'), token=token, request_kwargs=request_kwargs)

                except InvalidToken:
                    logger.error('Invalid Token : {}'.format(token))
                    return

                except TelegramError as er:
                    logger.error('Error : {}'.format(repr(er)))
                    return

            cb.setup()
            self.bots.append(cb)
            time.sleep(1)
