from __future__ import annotations
from abc import ABC, abstractmethod

from django.utils.timezone import make_aware

import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler,  Filters

from .models import User, UserState, Invitation, Meeting, Message
from .clock import Clock
from .vars import *

from django.db.models import Q

from django.core.exceptions import ObjectDoesNotExist

import logging
logger = logging.getLogger('connector.apps')

from dictdiffer import diff

import datetime

class Chatbot:
    token = None
    community_name = ''
    request_kwargs = None
    updater = None

    dialogs = []

    def __init__(self, community_name, token, request_kwargs=None):
        self.community_name = community_name
        self.token = token
        self.request_kwargs = request_kwargs
        self.updater = Updater(token=self.token, request_kwargs=self.request_kwargs)

    @property
    def bot(self):
        return self.updater.bot

    @property
    def username(self):
        return self.bot.username

    @property
    def dispatcher(self):
        return self.updater.dispatcher

    def setup(self):
        self.dispatcher.add_handler(CommandHandler("start", self.start_command_handler))
        self.dispatcher.add_handler(CommandHandler("info", self.info_command_handler))
        self.dispatcher.add_handler(CommandHandler("feedback", self.feedback_command_handler))
        self.dispatcher.add_handler(CommandHandler("status", self.status_command_handler))
        self.dispatcher.add_handler(MessageHandler(Filters.text | Filters.contact, self.general_message_handler))
        self.dispatcher.add_handler(CallbackQueryHandler(self.callback_query_handler))

    def get_dialog(self, user: User) -> Dialog:
        logger.info("DIALOG LOOKUP IN CACHE")
        dialog_list = list(filter(lambda x: x.chat_id == user.telegram_id, self.dialogs))

        if len(dialog_list) == 0:
            logger.info("dialog NOT FOUND")
            logger.info("initializing dialog")
            # TODO refactor to avoid calling globals
            dialog = Dialog(community_name=self.community_name, bot=self.bot, user=user)
            dialog.user.check_in()
            self.dialogs.append(dialog)
            logger.info("---")
            return dialog
        elif len(dialog_list) == 1:
            logger.info("dialog FOUND")
            dialog_list[0].user.check_in()
            return dialog_list[0]
        else:
            raise Exception('Too many dialogs with same user in cache')


    @staticmethod
    def send_menu_description(bot, chat_id):
        bot.send_message(
            text=MENU_DESCRIPTION,
            chat_id=chat_id,
            reply_markup=telegram.ReplyKeyboardRemove()
        )

    def status_command_handler(self, bot, update):
        logger.info("status_command_handler")
        try:
            user = User.objects.get(telegram_id=update.effective_user.id)
        except ObjectDoesNotExist:
            user = None

        if user is None:
            bot.send_message(
                chat_id=update.message.chat_id,
                text="User with ID %d never clicked /start" % update.effective_user.id,
                parse_mode=telegram.ParseMode.HTML,
            )
        else:
            dialog = self.get_dialog(user=user)

            status_text = "<b>User Telegram ID:</b> %s \n" % (user.telegram_id) + \
            "<b>User state, level 1 (database):</b> %s \n" % (user.state_context_saved) + \
            "<b>Dialog state, level 1 (bot cache):</b> %s \n" % (dialog._state.context)
            bot.send_message(
                chat_id=update.message.chat_id,
                text=status_text,
                parse_mode=telegram.ParseMode.HTML,
            )

    def start_command_handler(self, bot, update):
        logger.info("start_command_handler")

        user = None
        try:
            user = User.objects.get(telegram_id=update.effective_user.id)
        except ObjectDoesNotExist:
            pass

        if user is None:
            new_user = User(
                telegram_id=update.effective_user.id,
                first_name=update.effective_user.first_name if not update.effective_user.first_name is None else '',
                last_name=update.effective_user.last_name if not update.effective_user.last_name is None else '',
                telegram_username=update.effective_user.username if not update.effective_user.username is None else '',
            )
            new_user.save()

            new_user_from_db = User.objects.get(telegram_id=update.effective_user.id)

            new_user_state = UserState(user=new_user_from_db)
            new_user_state.save()

            dialog = self.get_dialog(user=new_user_from_db)
            dialog.transition_to(WelcomeNewUserState())
        else:
            dialog = self.get_dialog(user=user)

            if user.finished_registration:
                dialog.transition_to(UserProfileState())
            else:
                dialog.transition_to(WelcomeExistingUserState())

    def info_command_handler(self, bot, update):
        logger.info("info_command_handler")
        random_coffee_description = "<b>Random Coffee</b> — социальная игра, в которой ты будешь каждую неделю знакомиться с новым случайным человеком.\n\n" + \
                                    "Чтобы попасть в игру, нужно зарегистрироваться и принять приглашение на следующую встречу. Чат-бот подберет тебе собеседника и свяжет с ним в Телеграме.\n\n" + \
                                    "Правил нет, но есть рекомендация: держи телефон заряженным."
        bot.send_message(
            chat_id=update.message.chat_id,
            text=random_coffee_description,
            parse_mode=telegram.ParseMode.HTML,
        )
        self.send_menu_description(bot, update.message.chat_id)

    def feedback_command_handler(self, bot, update):
        logger.info("feedback_command_handler")
        try:
            user = User.objects.get(telegram_id=update.effective_user.id)
            dialog = self.get_dialog(user=user)
            dialog.transition_to(AskFeedbackState())
        except ObjectDoesNotExist:
            user = None
            # TODO: decide what to do if user not found

    def general_message_handler(self, bot, update):
        logger.info("")
        logger.info("")
        logger.info(update.message.text)
        logger.info("general_message_handler")
        try:
            user = User.objects.get(telegram_id=update.effective_user.id)
            dialog = self.get_dialog(user)
            dialog.reply_to_message(update)
        except ObjectDoesNotExist:
            user = None
            # TODO: decide what to do if user not found

    def callback_query_handler(self, bot, update):
        logger.info("callback_query_handler")
        try:
            user = User.objects.get(telegram_id=update.effective_user.id)
            dialog = self.get_dialog(user)
            dialog.reply_to_callback_query(update)
        except ObjectDoesNotExist:
            user = None
            # TODO: decide what to do if user not found


class Dialog:
    bot = None
    user = None
    _state = None

    @property
    def chat_id(self):
        return self.user.telegram_id

    def __init__(self, community_name, bot: Chatbot, user: User) -> None:
        self.community_name = community_name
        self.bot = bot
        self.user = user

        self.restore_dialog_state()

    # db state is master no matter what
    def restore_dialog_state(self):
        logger.info("CHECKING STATE BEFORE RESTORE SAVE")

        user_state_in_db = None
        try:
            user_state_in_db = UserState.objects.get(user=self.user)
        except ObjectDoesNotExist:
            pass

        logger.info("restoring state")
        if user_state_in_db is not None:
            # re-querying user object to fetch updated state_saved in db
            # turns out this self.user stores copy of instance, not list to it's representation in db
            # state is stored in db as dict. example:
            # { 'state_name': 'Example State', 'params': { 'p1': 1, 'p2': 2 } }
            from ast import literal_eval
            db_context = literal_eval(user_state_in_db.context)
            logger.info('db state: %s' % str(db_context))

            if db_context['state_name'] in globals().keys():
                user_state_restored_from_db = globals()[db_context['state_name']](params=db_context['params'])
            else:
                # almost impossible case if non-existent state is recorded in database
                user_state_restored_from_db = ErrorState()

            if self._state is None:
                logger.info("cache state is undefined, transitioning to db state")
                self.transition_to(user_state_restored_from_db, silent_enter=True)
            else:
                logger.info("cache state is cached")

                cached_context = self._state.context

                logger.info("comparing state versions in cache and db")
                logger.info("cache state name: %s" % cached_context['state_name'])
                logger.info("db state name: %s" % db_context['state_name'])

                if len(list(diff(cached_context, db_context))) > 0:
                    logger.info("db state is different, transitioning to db state")
                    self.transition_to(user_state_restored_from_db, silent_enter=True)
                else:
                    logger.info("db state equals cache state, aborting transition")
        else:
            logger.info("user state in dialog is not initialized in db, aborting transition")

    def transition_to(self, state: DialogState, silent_enter=False):
        logger.info("TRANSITION TO %s" % state.context['state_name'])
        if not (self._state is None):
            self.send_farewell_message(silent_enter=silent_enter)

        logger.info("SETTING STATE")
        self._state = state
        self._state.dialog = self
        self._state.dialog.user = User.objects.get(telegram_id=self._state.dialog.user.telegram_id)
        self._state.update_context()

        logger.info("TRANSITION FINISHED")
        logger.info("sending welcome message from new state")
        self.send_welcome_message(silent_enter=silent_enter)

    def send_message(self, text, reply_markup=None, parse_mode=None, chat_id=None, one_time_keyboard=None):
        if reply_markup is None:
            reply_markup = telegram.ReplyKeyboardRemove()

        if chat_id is None:
            chat_id = self.chat_id

        if parse_mode is None:
            parse_mode = telegram.ParseMode.HTML

        if one_time_keyboard is None:
            one_time_keyboard = False

        m = self.bot.send_message(
            text=text,
            reply_markup=reply_markup,
            chat_id=chat_id,
            parse_mode=parse_mode,
            one_time_keyboard=one_time_keyboard
        )

        # naive logging
        #TODO: log reply_markup
        try:
            Message(
                user=self.user,
                direction="out",
                text=str(text),
                message_id=m.message_id
            ).save()
        except Exception as e:
            logger.error(e)
            print(e)

        return m

    def send_welcome_message(self, silent_enter=False):
        logger.info("CALLING send_welcome_message, silent_enter=%s" % str(silent_enter))
        #self.restore_dialog_state()
        self._state.handle_entering_state(silent_enter=silent_enter)

    def reply_to_callback_query(self, update):
        # TODO: add naive logging for callbacks
        logger.info("CALLING reply_to_callback_query")
        self.restore_dialog_state()
        self._state.handle_callback_query(update)

    def reply_to_message(self, update):
        # naive logging
        try:
            Message(
                user=self.user,
                direction="in",
                text=str(update.message.text),
                message_id=update.message.message_id
            ).save()
        except Exception as e:
            logger.error(e)
            print(e)
        logger.info("CALLING reply_to_message")
        self.restore_dialog_state()
        self._state.handle_message(update)

    def send_farewell_message(self, silent_enter=False):
        logger.info("CALLING send_farewell_message, silent_enter=%s" % str(silent_enter))
        #self.restore_dialog_state()
        self._state.handle_leaving_state(silent_enter=silent_enter)

    def thank_user(self):
        self.send_message(
            text="Спасибо!",
        )

    def fall_back(self, silent_enter=False):
        self.send_message(
            text="Не понимаю твой ответ. Давай попробуем еще раз.",
        )
        self.send_welcome_message(silent_enter)


class DialogState(ABC):
    _context = None
    _dialog = None

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        self.context = DialogState.set_default_params(context_dict)

    @classmethod
    def set_default_params(cls, context_dict):
        logger.info(context_dict['params'])
        if not 'stop_after_finish' in context_dict['params'].keys():
            context_dict['params']['stop_after_finish'] = False
        return context_dict

    @property
    def context(self) -> dict:
        return self._context

    @context.setter
    def context(self, context: dict) -> None:
        self._context = context

    def update_context_stage(self, stage=0):
        user_state = UserState.objects.get(user=self.dialog.user)
        self.context['params']['stage'] = stage
        user_state.context = str(self.context)
        user_state.save()

    def update_context(self):
        user_state = UserState.objects.get(user=self.dialog.user)
        user_state.context = str(self.context)
        user_state.context = str(self.context)
        user_state.save()

    @property
    def dialog(self) -> Dialog:
        return self._dialog

    @dialog.setter
    def dialog(self, dialog: Dialog) -> None:
        self._dialog = dialog

    @abstractmethod
    def handle_entering_state(self, silent_enter=False) -> None:
        pass

    @abstractmethod
    def handle_callback_query(self, update) -> None:
        pass

    @abstractmethod
    def handle_message(self, update) -> None:
        pass

    @abstractmethod
    def handle_leaving_state(self, silent_enter=False) -> None:
        pass


class NullState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

    def handle_message(self, update) -> None:
        self.dialog.send_message(
            text="Не знаю, как на это реагировать...",
        )

    def handle_callback_query(self, update) -> None:
        s = UserProfileState()
        s.dialog = self.dialog
        s.handle_callback_query(update)

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return


class ErrorState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        self.dialog.send_message(
            text="Простите, но в работе бота произошла ошибка. Перезагружаю ваш диалог с ним.",
        )

    def handle_message(self, update) -> None:
        pass

    def handle_callback_query(self, update) -> None:
        pass

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter: return


class UserProfileState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        user = self.dialog.user

        meetings_status_html = """\n\nУчаствует на этой неделе: <i>{accepted_invitation_this_week}</i>\nУчаствует на следующей неделе: <i>{accepted_invitation_next_week}</i>\n\n""" \
            .format(
                accepted_invitation_this_week="Да" if not user.invitation_this_week is None and user.invitation_this_week.accepted else "Hет",
                accepted_invitation_next_week="Да" if not user.invitation_next_week is None and user.invitation_next_week.accepted else "Hет",
            )

        profile_html = """<b>Профиль участника Random Coffee {community_name}</b>\n\nНикнейм в Телеграме: <i>{telegram_username}</i>\nИмя: <i>{first_name}</i>\nФамилия: <i>{last_name}</i>\nТелефон: <i>{phone_number}</i>\nКомпания: <i>{group}</i>\nЧастота встреч: <i>{frequency}</i>\nМотивация встреч: <i>{motivation}</i>\nО себе: <i>{about}</i>{meetings_status_html}{registered_at}{menu_description}""" \
            .format(
            community_name=self.dialog.community_name,
            first_name=user.first_name,
            last_name=user.last_name if len(user.last_name) > 0 else '-',
            telegram_username=user.telegram_username if user.telegram_username is not None else 'не задан',
            phone_number=user.phone_number if len(user.phone_number) > 0 else 'не указан',
            group=user.group.name if user.group is not None else '-',
            frequency=list(filter(lambda x: x[0] == user.meeting_frequency, MEETING_FREQUENCY_CHOICES))[0][1],
            motivation=list(filter(lambda x: x[0] == user.meeting_motivation, MOTITVATION_CHOICES))[0][1],
            about=user.about if len(user.about) > 0 else '-',
            meetings_status_html="%s" % (meetings_status_html) if user.registered_at is not None else "\n\n",
            registered_at="Зарегистрирован %s" % (user.registered_at.strftime(
                "%d.%m.%Y")) if user.registered_at is not None else '😧 Регистрация пройдена не до конца. Чтобы завершить ее, выполни команду /start',
            menu_description=MENU_DESCRIPTION
        )

        reply_markup = telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton(text="✏️ 1. Имя", callback_data="profile_edit_first_name"),
                telegram.InlineKeyboardButton(text="✏️ 2. Фамилия", callback_data="profile_edit_last_name"),
            ],
            [
                telegram.InlineKeyboardButton(text="✏️ 3. Телефон", callback_data="profile_edit_phone_number"),
                telegram.InlineKeyboardButton(text="✏️ 4. Компания", callback_data="profile_edit_company"),
            ],
            [
                telegram.InlineKeyboardButton(text="✏️ 5. Частота встреч", callback_data="profile_edit_meeting_frequency"),
                telegram.InlineKeyboardButton(text="✏️ 6. О себе", callback_data="profile_edit_about"),
            ],
            [
                telegram.InlineKeyboardButton(text="✏️ 7. Мотивация встречи",
                                              callback_data="profile_edit_meeting_motivation")
            ]
        ])

        self.dialog.send_message(
            text=profile_html,
            reply_markup=reply_markup
        )

    def handle_message(self, update) -> None:
        pass

    def handle_callback_query(self, update) -> None:
        if update.callback_query.data == 'profile_edit_first_name':
            self.dialog.transition_to(EditFirstNameState(params={'stage': 0, 'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_last_name':
            self.dialog.transition_to(EditLastNameState(params={'stage': 0, 'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_company':
            self.dialog.transition_to(EditCompanyState(params={'stage': 0, 'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_about':
            self.dialog.transition_to(EditAboutYourselfState(params={'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_phone_number':
            self.dialog.transition_to(EditPhoneNumberState(params={'stage': 0, 'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_meeting_frequency':
            self.dialog.transition_to(EditMeetingsFrequencyState(params={'stop_after_finish':True}))

        if update.callback_query.data == 'profile_edit_meeting_motivation':
            self.dialog.transition_to(EditMeetingsMotivationState(params={'stop_after_finish':True}))

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter: return


class AskFeedbackState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.send_message(
            text='Поделись своим общим впечатлечением о сервисе и расскажи, чего тебе не хватает'
        )

    def handle_message(self, update) -> None:
        from .models import Feedback
        feedback = Feedback(user=self.dialog.user, text=update.message.text)
        feedback.save()
        self.dialog.send_message(
            text='Спасибо за твой отзыв! Мы внимательно его изучим и при необходимости свяжемся с тобой.'
        )
        self.dialog.transition_to(NullState())

    def handle_callback_query(self, update) -> None:
        pass

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter: return


class ReplyToMeetingInvitationState(DialogState):
    __AWAITING_DECISION, __AWAITING_CANCELLATION_FEEDBACK = range(2)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_DECISION
        self.context = DialogState.set_default_params(context_dict)

    def handle_entering_state(self, silent_enter=False) -> None:
        now = make_aware(datetime.datetime.now())
        year_now, week_now = Clock.get_iso_week(now)

        inv = None
        try:
            inv = Invitation.objects.get(
                user=self.dialog.user,
                year=self.context['params']['year'],
                week=self.context['params']['week']
            )
        except ObjectDoesNotExist:
            pass

        if self.context['params']['stage'] == self.__AWAITING_DECISION:
            if inv is None:
                inv = Invitation(
                    user=self.dialog.user,
                    year=self.context['params']['year'],
                    week=self.context['params']['week']
                )

            try:
                if silent_enter:
                    inv.save()
                else:
                    print("sending invite")

                    reply_markup = telegram.ReplyKeyboardMarkup(
                        [
                            [telegram.KeyboardButton(text="Да, конечно"),
                             telegram.KeyboardButton(text="Пожалуй, нет")]
                        ],
                        one_time_keyboard=True
                    )

                    year_next_week_hypo, week_next_week_hypo = Clock.get_next_week_by_year_and_week(year_now, week_now)

                    if self.context['params']['year'] == year_next_week_hypo and self.context['params']['week'] == week_next_week_hypo:
                        text = "Снова здравствуйте! Хочешь ли встретиться с кем-то на следующей неделе (%s)?" \
                                  % Clock.get_week_boundaries_readable(self.context['params']['year'], self.context['params']['week'])
                    else:
                        text = "Снова здравствуйте! Хочешь ли встретиться с кем-то на неделе %s?" \
                                  % Clock.get_week_boundaries_readable(self.context['params']['year'], self.context['params']['week'])

                    m = self.dialog.send_message(
                        text=text,
                        reply_markup=reply_markup
                    )

                    inv.message_id = m.message_id
                    inv.sent_at = now
                    inv.counter += 1

                    inv.save()
            except Exception as e:
                print(e)
                logger.info(e)
            return

        if self.context['params']['stage'] == self.__AWAITING_CANCELLATION_FEEDBACK:
            if silent_enter: return

            reply_markup = telegram.ReplyKeyboardMarkup([
                [telegram.KeyboardButton(text=NO_TIME_REPLY)],
                [telegram.KeyboardButton(text=NOT_IN_MOOD_REPLY)],
                [telegram.KeyboardButton(text=NO_INTEREST_REPLY)]
            ])

            self.dialog.send_message(
                text="Почему так?",
                reply_markup=reply_markup
            )
            return

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        now = make_aware(datetime.datetime.now())

        inv = None
        try:
            inv = Invitation.objects.get(
                user=self.dialog.user,
                year=self.context['params']['year'],
                week=self.context['params']['week']
            )
        except ObjectDoesNotExist:
            pass

        if inv is not None:
            if self.context['params']['stage'] == self.__AWAITING_DECISION:
                if update.message.text == "Да, конечно":
                    inv.accepted = True
                    inv.cancel_reason = ''
                    inv.decided_at = now
                    inv.save()

                    self.dialog.thank_user()
                    self.dialog.transition_to(NullState())
                elif update.message.text == "Пожалуй, нет":
                    inv.accepted = False
                    inv.cancel_reason = ''
                    inv.decided_at = now
                    inv.save()

                    self.update_context_stage(self.__AWAITING_CANCELLATION_FEEDBACK)
                    self.handle_entering_state()

                new_meeting_schedule = inv.trigger_rearrange_meetings()
                logger.info(new_meeting_schedule)

                return

            if self.context['params']['stage'] == self.__AWAITING_CANCELLATION_FEEDBACK:
                if update.message.text in list(map(lambda x: x[1], CANCELLATION_REASON_CHOICES)):


                    inv.cancel_reason = list(filter(lambda x: x[1] == update.message.text, CANCELLATION_REASON_CHOICES))[0][0]
                    inv.save()

                    self.dialog.thank_user()
                    self.dialog.transition_to(NullState())
                else:
                    self.dialog.fall_back()
                return
        else:
            self.dialog.send_message(
                text="Не могу сопоставить твой ответ с действующим приглашением. Давай просто подождем следующей встречи.",
            )

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return


class CollectMeetingFeedbackState(DialogState):
    __AWAITING_MEETING_CONFIRMATION, __AWAITING_MEETING_RATING, __AWAITING_ARRANGEMENT_FAILURE_REASON = range(3)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_MEETING_CONFIRMATION
        self.context = DialogState.set_default_params(context_dict)

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        if self.context['params']['stage'] == self.__AWAITING_MEETING_CONFIRMATION:
            m = Meeting.get_instance_by_unique_parameters(
                year=self.context['params']['year'],
                week=self.context['params']['week'],
                user_1_telegram_id=self.context['params']['partner_id'],
                user_2_telegram_id=self.dialog.user.telegram_id
            )

            if m is None:
                logger.error("Meeting not found")
                self.dialog.transition_to(NullState())

            reply_markup = telegram.ReplyKeyboardMarkup(
                [
                    [telegram.KeyboardButton(text=POSITIVE_REPLY),
                     telegram.KeyboardButton(text=NEGATIVE_REPLY)]
                ],
                one_time_keyboard=True
            )

            partner = User.objects.get(telegram_id=self.context['params']['partner_id'])
            week_boundaries_readable = Clock.get_week_boundaries_readable(
                year=self.context['params']['year'],
                week=self.context['params']['week']
            )
            message_text = "Привет! Быстрый вопрос. \n\nНа неделе №%d (%s) " % (self.context['params']['week'], week_boundaries_readable) + \
                     "у тебя должна была быть встреча с <b>%s</b>.\n\n" % partner.full_name + \
                     "У вас получилось встретиться?"

            m = self.dialog.send_message(
                text=message_text,
                reply_markup=reply_markup
            )
            return

        if self.context['params']['stage'] == self.__AWAITING_MEETING_RATING:
            reply_markup = telegram.ReplyKeyboardMarkup(
                [
                    [telegram.KeyboardButton(text=POSITIVE_REPLY),
                     telegram.KeyboardButton(text=NEGATIVE_REPLY)]
                ],
                one_time_keyboard=True
            )

            self.dialog.send_message(
                text="Тебе понравилось, как все прошло?",
                reply_markup=reply_markup
            )

        if self.context['params']['stage'] == self.__AWAITING_ARRANGEMENT_FAILURE_REASON:
            reply_markup = telegram.ReplyKeyboardMarkup([
                [telegram.KeyboardButton(text=HAVENT_CONTACTED_REPLY)],
                [telegram.KeyboardButton(text=COULDNT_ARRANGE_REPLY)],
                [telegram.KeyboardButton(text=FORCED_MAJOR_REPLY)]
            ])

            self.dialog.send_message(
                text="Почему так?",
                reply_markup=reply_markup
            )

            return

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        m = Meeting.get_instance_by_unique_parameters(
            year=self.context['params']['year'],
            week=self.context['params']['week'],
            user_1_telegram_id=self.context['params']['partner_id'],
            user_2_telegram_id=self.dialog.user.telegram_id
        )

        if self.context['params']['stage'] == self.__AWAITING_MEETING_CONFIRMATION:
            if not update.message.text in [POSITIVE_REPLY, NEGATIVE_REPLY]:
                self.dialog.fall_back()

            meeting_took_place = update.message.text == POSITIVE_REPLY

            if m.user_a_telegram_id == self.dialog.user.telegram_id:
                m.user_a_meeting_took_place = meeting_took_place
            else:
                m.user_b_meeting_took_place = meeting_took_place
            m.save()

            if meeting_took_place:
                self.update_context_stage(self.__AWAITING_MEETING_RATING)
                self.handle_entering_state()
            else:
                self.update_context_stage(self.__AWAITING_ARRANGEMENT_FAILURE_REASON)
                self.handle_entering_state()
            return

        if self.context['params']['stage'] == self.__AWAITING_MEETING_RATING:
            if not update.message.text in [POSITIVE_REPLY, NEGATIVE_REPLY]:
                self.dialog.fall_back()

            happiness = update.message.text == POSITIVE_REPLY

            if m.user_a_telegram_id == self.dialog.user.telegram_id:
                m.user_a_happy = happiness
            else:
                m.user_b_happy = happiness
            m.save()

            unrated_meeting_same_week = self.dialog.user.find_unrated_meeting(year=self.context['params']['year'], week=self.context['params']['week'])
            if unrated_meeting_same_week is None:
                self.dialog.transition_to(NullState())
            else:
                self.dialog.transition_to(CollectMeetingFeedbackState(params={
                    "partner_id": unrated_meeting_same_week.get_partner_id(self.dialog.user.telegram_id),
                    "year": self.context['params']['year'],
                    "week": self.context['params']['week']
                }))

        if self.context['params']['stage'] == self.__AWAITING_ARRANGEMENT_FAILURE_REASON:
            if not update.message.text in list(map(lambda x: x[1], ARRANGEMENT_FAILURE_REASONS)):
                self.dialog.fall_back()

            failure_reason = list(filter(lambda x: x[1] == update.message.text, ARRANGEMENT_FAILURE_REASONS))[0][0]

            if m.user_a_telegram_id == self.dialog.user.telegram_id:
                m.user_a_meeting_failure_reason = failure_reason
            else:
                m.user_b_meeting_failure_reason = failure_reason
            m.save()

            unrated_meeting_same_week = self.dialog.user.find_unrated_meeting(year=self.context['params']['year'],
                                                                              week=self.context['params']['week'])
            if unrated_meeting_same_week is None:
                self.dialog.transition_to(NullState())
            else:
                self.dialog.transition_to(CollectMeetingFeedbackState(params={
                    "partner_id": unrated_meeting_same_week.get_partner_id(self.dialog.user.telegram_id),
                    "year": self.context['params']['year'],
                    "week": self.context['params']['week']
                }))

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class WelcomeNewUserState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup(
            [
                [telegram.KeyboardButton(text="Регистрация")],
            ],
            one_time_keyboard=True
        )
        self.dialog.send_message(
            text=("Привет!\n\nНажми на кнопку \"Регистрация\" внизу, чтобы присоединиться к Random Coffee в \"%s\"") % (self.dialog.community_name),
            reply_markup=reply_markup
        )

    def handle_message(self, update) -> None:
        if update.message.text == "Регистрация":
            self.dialog.send_message(
                text="Осталось заполнить анкету о себе из 8 вопросов. Поехали!",
                chat_id=update.message.chat.id
            )
            self.dialog.transition_to(EditGenderState())
        else:
            reply_markup = telegram.ReplyKeyboardMarkup(
                [
                    [telegram.KeyboardButton(text="Регистрация")],
                ],
                one_time_keyboard=True
            )
            #TODO: convert to fall_back
            self.dialog.send_message(
                text=("Не совсем тебя понял. Ты хотел зарегистрироваться? Тогда просто нажми кнопку внизу."),
                reply_markup=reply_markup
            )

    def handle_callback_query(self, update) -> None:
        pass

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return


class WelcomeExistingUserState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup(
            [
                [telegram.KeyboardButton(text="Регистрация")],
            ],
            one_time_keyboard=True
        )
        self.dialog.send_message(
            text=("Привет!\n\nКажется, в прошлый раз регистрация сорвалась.\n\nДавай быстренько пройдем ее заново. Нажми на кнопку \"Регистрация\" внизу экрана"),
            reply_markup=reply_markup
        )

    def handle_message(self, update) -> None:
        if update.message.text == "Регистрация":
            self.dialog.send_message(
                text="Осталось заполнить анкету о себе из 8 вопросов. Поехали!",
                chat_id=update.message.chat.id
            )
            self.dialog.transition_to(EditGenderState())
        else:
            pass

    def handle_callback_query(self, update) -> None:
        pass

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return


class EditGenderState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup(
            [
                [telegram.KeyboardButton(text='🙋‍♂️️'),
                 telegram.KeyboardButton(text='🙋')]
            ],
            one_time_keyboard=True
        )
        self.dialog.send_message(
            text="1. Укажи, пожалуйста, свой пол",
            reply_markup=reply_markup
        )
        pass

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if update.message.text == '🙋‍♂️️':
            self.dialog.user.gender = MALE
            self.dialog.user.save()
        elif update.message.text == '🙋':
            self.dialog.user.gender = FEMALE
            self.dialog.user.save()

        if not self.context['params']['stop_after_finish']:
            self.dialog.transition_to(EditFirstNameState())
        else:
            self.dialog.transition_to(NullState())

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditFirstNameState(DialogState):
    __AWAITING_INPUT, __AWAITING_CONFIRMATION = range(2)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_CONFIRMATION
        self.context = DialogState.set_default_params(context_dict)

    def ask_for_input(self):
        self.dialog.send_message(
            text='2. Пришли имя, которое хочешь использовать',
        )

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        if self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if self.dialog.user.first_name == '':
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()
                return
            else:
                reply_markup = telegram.ReplyKeyboardMarkup(
                    [
                        [telegram.KeyboardButton(text="Да")],
                        [telegram.KeyboardButton(text="Нет, хочу другое имя")]
                    ],
                    one_time_keyboard=True
                )
                self.dialog.send_message(
                    text="2. Проверь свое имя: %s. Верно?" % (self.dialog.user.first_name),
                    reply_markup=reply_markup
                )

        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            self.ask_for_input()

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            self.dialog.user.first_name = update.message.text
            self.dialog.user.save()
            self.update_context_stage(self.__AWAITING_CONFIRMATION)
            self.handle_entering_state()
            return
        elif self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if update.message.text == "Да":
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditLastNameState())
                else:
                    self.dialog.transition_to(NullState())
            elif update.message.text == "Нет, хочу другое имя":
                self.update_context_stage(self. __AWAITING_INPUT)
                self.ask_for_input()

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditLastNameState(DialogState):
    __AWAITING_INPUT, __AWAITING_CONFIRMATION = range(2)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_CONFIRMATION
        self.context = DialogState.set_default_params(context_dict)

    def ask_for_input(self):
        reply_markup = telegram.ReplyKeyboardMarkup(
            [
                [telegram.KeyboardButton(text="Пропустить")]
            ],
            one_time_keyboard=True
        )

        self.dialog.send_message(
            text='3. Пришли фамилию, которую хочешь использовать. Можешь оставить поле пустым, нажав кнопку внизу.',
            reply_markup=reply_markup
        )

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        if self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if self.dialog.user.last_name == '':
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()
                return
            else:
                reply_markup = telegram.ReplyKeyboardMarkup(
                    [
                        [telegram.KeyboardButton(text="Да")],
                        [telegram.KeyboardButton(text="Нет, у меня другая фамилия")]
                    ],
                    one_time_keyboard=True
                )
                self.dialog.send_message(
                    text="3. Проверь свою фамилию: %s. Верно?" % (self.dialog.user.last_name),
                    reply_markup=reply_markup
                )

        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            self.ask_for_input()

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            if update.message.text == 'Пропустить':
                self.dialog.user.last_name = ''
                self.dialog.user.save()
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditPhoneNumberState())
                else:
                    self.dialog.transition_to(NullState())
            else:
                self.dialog.user.last_name = update.message.text
                self.dialog.user.save()
                self.update_context_stage(self.__AWAITING_CONFIRMATION)
                self.handle_entering_state()
        elif self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if update.message.text == "Да":
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditPhoneNumberState())
                else:
                    self.dialog.transition_to(NullState())
            elif update.message.text == "Нет, у меня другая фамилия":
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditPhoneNumberState(DialogState):
    __AWAITING_INPUT, __AWAITING_CONFIRMATION = range(2)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_CONFIRMATION
        self.context = DialogState.set_default_params(context_dict)

    def give_hint_typo_in_phone_number(self):
        self.dialog.send_message(
            text="Кажется, в номере есть ошибка. Попробуй еще раз.",
        )

    def ask_for_input(self):
        share_contact_button = telegram.KeyboardButton(
            text="Отправить номер телефона из Телеграма",
            request_contact=True
        )
        reply_markup = telegram.ReplyKeyboardMarkup(
            [
                [share_contact_button]
            ]
        )
        self.dialog.send_message(
            text='4. Пришли, пожалуйста, свой номер телефона. Для этого нажми кнопку внизу экрана или отправь его в сообщении.',
            reply_markup=reply_markup
        )

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        if self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if self.dialog.user.phone_number == '':
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()
                return
            else:
                reply_markup = telegram.ReplyKeyboardMarkup(
                    [
                        [telegram.KeyboardButton(text="Верно")],
                        [telegram.KeyboardButton(text="Неверно, есть ошибка")]
                    ],
                    one_time_keyboard=True
                )
                self.dialog.send_message(
                    text="4*. Проверь свой номер телефона: %s" % (self.dialog.user.phone_number),
                    reply_markup=reply_markup
                )

        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            self.ask_for_input()

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if self.context['params']['stage'] == self.__AWAITING_CONFIRMATION:
            if update.message.text == "Верно":
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditCompanyState())
                else:
                    self.dialog.transition_to(NullState())
            elif update.message.text == "Неверно, есть ошибка":
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()
        elif self.context['params']['stage'] == self.__AWAITING_INPUT:
            import phonenumbers
            try:
                z = update.message.contact.phone_number
            except:
                z = update.message.text
            # some telegram clients send phonee numbers without leading "+"
            if z[0] == "+":
                pass
            else:
                z = "+%s" % (z)
            try:
                z_parsed = phonenumbers.parse(z, None)
            except phonenumbers.phonenumberutil.NumberParseException as e:
                self.give_hint_typo_in_phone_number()
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()

            if phonenumbers.is_possible_number(z_parsed):
                self.dialog.user.phone_number = phonenumbers.format_number(z_parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                self.dialog.user.save()
                self.update_context_stage(self.__AWAITING_CONFIRMATION)
                self.handle_entering_state()
            else:
                self.give_hint_typo_in_phone_number()
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditCompanyState(DialogState):
    __MAX_GROUPS_ON_SCREEN = 5
    __AWAITING_TYPE, __AWAITING_SELECT_GROUP, __AWAITING_INPUT = range(3)

    def __init__(self, params={}):
        context_dict = dict({'state_name': type(self).__name__})
        context_dict['params'] = params
        if not 'stage' in context_dict['params'].keys():
            context_dict['params']['stage'] = self.__AWAITING_TYPE
        self.context = DialogState.set_default_params(context_dict)

    def get_groups(self):
        from .models import Group
        groups_set = Group.objects.order_by().values('name').distinct()
        groups = list(map(lambda x: x['name'], groups_set))
        groups = list(filter(lambda x: x != '', groups))
        return groups

    def ask_for_input(self):
        self.dialog.send_message(
            text="5*. Ок, тогда пришли название вашей компании. \
            Лучше, если оно будет полным, чтобы твоим коллегам было проще его распознать",
        )

    def ask_to_select_group(self):
        groups = self.get_groups()

        if len(groups) == 0:
            self.update_context_stage(self.__AWAITING_INPUT)
            self.ask_for_input()
        else:
            self.update_context_stage(self.__AWAITING_SELECT_GROUP)

            self.dialog.send_message(
                text="5*. Ок, попробуй найти вашу компанию в списке"
            )

            reply_markup_dict = list(map(
                lambda x: [telegram.InlineKeyboardButton(
                    text=x,
                    callback_data="select|%s" % (x.replace("|", ""))
                )],
                groups[:self.__MAX_GROUPS_ON_SCREEN]))

            if len(groups) > self.__MAX_GROUPS_ON_SCREEN:
                reply_markup_dict.append([telegram.InlineKeyboardButton(text="⬇️", callback_data="show_next|0")])
            else:
                reply_markup_dict.append([telegram.InlineKeyboardButton(text="Не могу найти", callback_data="add_new")])
            reply_markup = telegram.InlineKeyboardMarkup(reply_markup_dict)
            self.dialog.send_message(
                text="Сохраненные компании (можешь добавить свою):",
                reply_markup=reply_markup
            )

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        if self.context['params']['stage'] == self.__AWAITING_TYPE:
            reply_markup = telegram.ReplyKeyboardMarkup([
                [telegram.KeyboardButton(text=INDIVIDUAL_TYPE_REPLY)],
                [telegram.KeyboardButton(text=TEAM_TYPE_REPLY)]
            ])
            self.dialog.send_message(
                text="5. В коворкинге ты один или с коллегами?",
                reply_markup=reply_markup,
                one_time_keyboard=True
            )
        if self.context['params']['stage'] == self.__AWAITING_INPUT:
            self.ask_to_select_group()

        if self.context['params']['stage'] == self.__AWAITING_SELECT_GROUP:
            self.ask_to_select_group()

    def handle_callback_query(self, update) -> None:
        if self.context['params']['stage'] == self.__AWAITING_SELECT_GROUP:
            data_parsed = update.callback_query.data.split("|")

            if data_parsed[0] == 'select':
                group_name = str(data_parsed[1]).replace("|", "")
                from .models import Group
                self.dialog.user.group = Group.objects.filter(name=group_name)[0]
                self.dialog.user.save()
                self.dialog.bot.edit_message_text(
                    text="5**. Ты выбрал компанию %s" % (group_name),
                    chat_id=self.dialog.chat_id,
                    message_id=update.callback_query.message.message_id
                )
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditMeetingsFrequencyState())
                else:
                    self.dialog.transition_to(NullState())
            elif data_parsed[0] == 'show_next' or data_parsed[0] == 'show_previous':
                groups = self.get_groups()
                offset = int(data_parsed[1])
                if data_parsed[0] == 'show_next':
                    if offset + self.__MAX_GROUPS_ON_SCREEN < len(groups):
                        offset += self.__MAX_GROUPS_ON_SCREEN
                if data_parsed[0] == 'show_previous':
                    if offset - self.__MAX_GROUPS_ON_SCREEN >= 0:
                        offset -= self.__MAX_GROUPS_ON_SCREEN
                reply_markup_dict = list(map(lambda x: [telegram.InlineKeyboardButton(text=x, callback_data="select|%s" % (x.replace("|", "")))], groups[offset:offset+self.__MAX_GROUPS_ON_SCREEN]))
                if offset > 0:
                    reply_markup_dict.insert(0, [telegram.InlineKeyboardButton(text="⬆️", callback_data="show_previous|%d" % (offset))])
                if len(groups) > offset + self.__MAX_GROUPS_ON_SCREEN:
                    reply_markup_dict.append([telegram.InlineKeyboardButton(text="⬇️", callback_data="show_next|%d" % (offset))])
                else:
                    reply_markup_dict.append([telegram.InlineKeyboardButton(text="Не могу найти", callback_data="add_new")])
                reply_markup = telegram.InlineKeyboardMarkup(reply_markup_dict)
                self.dialog.bot.edit_message_reply_markup(
                    reply_markup=reply_markup,
                    chat_id=self.dialog.chat_id,
                    message_id=update.callback_query.message.message_id
                )
            elif data_parsed[0] == 'add_new':
                self.update_context_stage(self.__AWAITING_INPUT)
                self.ask_for_input()

    def handle_message(self, update) -> None:
        if self.context['params']['stage'] == self.__AWAITING_TYPE:
            if update.message.text == INDIVIDUAL_TYPE_REPLY:
                self.dialog.user.type = INDIVIDUAL
                self.dialog.user.group = None
                self.dialog.user.save()
                if not self.context['params']['stop_after_finish']:
                    self.dialog.transition_to(EditMeetingsFrequencyState())
                else:
                    self.dialog.transition_to(NullState())
            elif update.message.text == TEAM_TYPE_REPLY:
                self.dialog.user.type = TEAM
                self.dialog.user.save()
                self.update_context_stage(self.__AWAITING_SELECT_GROUP)
                self.ask_to_select_group()
        elif self.context['params']['stage'] == self.__AWAITING_INPUT:
            from .models import Group
            new_group = Group(name=update.message.text.replace("|", ""))
            new_group.save()
            self.dialog.user.group = new_group
            self.dialog.user.save()
            if not self.context['params']['stop_after_finish']:
                self.dialog.transition_to(EditMeetingsFrequencyState())
            else:
                self.dialog.transition_to(NullState())

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditMeetingsFrequencyState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup([
            [telegram.KeyboardButton(text=HIGH_FREQUENCY_REPLY)],
            [telegram.KeyboardButton(text=MEDIUM_FREQUENCY_REPLY)],
            [telegram.KeyboardButton(text=LOW_FREQUENCY_REPLY)]
        ])
        self.dialog.send_message(
            text="6. Выбери, с какой частотой тебе хотелось бы ходить на встречи?",
            reply_markup=reply_markup
        )

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if update.message.text in [HIGH_FREQUENCY_REPLY, MEDIUM_FREQUENCY_REPLY, LOW_FREQUENCY_REPLY]:
            if update.message.text == HIGH_FREQUENCY_REPLY:
                self.dialog.user.meeting_frequency = HIGH
            elif update.message.text == MEDIUM_FREQUENCY_REPLY:
                self.dialog.user.meeting_frequency = MEDIUM
            elif update.message.text == LOW_FREQUENCY_REPLY:
                self.dialog.user.meeting_frequency = LOW

            self.dialog.user.save()

            if not self.context['params']['stop_after_finish']:
                self.dialog.transition_to(EditMeetingsMotivationState())
            else:
                self.dialog.transition_to(NullState())
        else:
            self.dialog.send_message(
                text="Не понимаю твой ответ. Давай попробуем еще раз.",
            )
            self.handle_entering_state()

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditMeetingsMotivationState(DialogState):
    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup([
            [telegram.KeyboardButton(text=DATING_REASON_REPLY)],
            [telegram.KeyboardButton(text=NETWORKING_REASON_REPLY)],
            [telegram.KeyboardButton(text=HAVING_FUN_REASON_REPLY)]
        ])
        self.dialog.send_message(
            text="7. Какая цель встречи тебе ближе всего?",
            reply_markup=reply_markup
        )

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if update.message.text in [DATING_REASON_REPLY, NETWORKING_REASON_REPLY, HAVING_FUN_REASON_REPLY]:
            if update.message.text == DATING_REASON_REPLY:
                self.dialog.user.meeting_motivation = DATING
            elif update.message.text == NETWORKING_REASON_REPLY:
                self.dialog.user.meeting_motivation = NETWORKING
            elif update.message.text == HAVING_FUN_REASON_REPLY:
                self.dialog.user.meeting_motivation = HAVING_FUN

            self.dialog.user.save()

            if not self.context['params']['stop_after_finish']:
                self.dialog.transition_to(EditAboutYourselfState())
            else:
                self.dialog.transition_to(NullState())
        else:
            self.dialog.send_message(
                text="Не понимаю твой ответ. Давай попробуем еще раз."
            )
            self.handle_entering_state()

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()


class EditAboutYourselfState(DialogState):
    def post_registration_activities(self):
        now = make_aware(datetime.datetime.now())
        year, week = Clock.get_next_iso_week()

        inv = Invitation(
            user=self.dialog.user,
            year=year,
            week=week,
            accepted=True,
            counter=1,
            decided_at=now
        )

        inv.save()

        inv.trigger_rearrange_meetings()

        self.dialog.send_message(
            text="Готово, регистрация позади!\n\nТы добавлен{he_or_she} в список участников следующей недели, приглашение придет в этот чат в ближайший понедельник или чуть позже.\n\nПока можешь посмотреть свой профиль, нажав /start.\n\nДо скорого!".format(
                he_or_she="а" if self.dialog.user.gender == FEMALE else ""
            )
        )

    def handle_entering_state(self, silent_enter=False) -> None:
        if silent_enter:
            return

        reply_markup = telegram.ReplyKeyboardMarkup([
            [telegram.KeyboardButton(text='Пропустить и заполнить потом')],
        ])

        self.dialog.send_message(
            text="8. Напиши пару предложений о себе для других участников.\n\nЕсли хочешь, можешь сделать это позже через страницу своего профиля.",
            reply_markup=reply_markup
        )

    def handle_callback_query(self, update) -> None:
        pass

    def handle_message(self, update) -> None:
        if update.message.text == 'Пропустить и заполнить потом':
            self.dialog.user.about = ''
            self.dialog.user.save()
        else:
            self.dialog.user.about = update.message.text
            self.dialog.user.save()

        if not self.dialog.user.finished_registration:
            self.dialog.user.registered_at = make_aware(datetime.datetime.now())
            self.dialog.user.save()
            self.post_registration_activities()
        else:
            self.dialog.transition_to(NullState())

    def handle_leaving_state(self, silent_enter=False) -> None:
        if silent_enter:
            return
        self.dialog.thank_user()
