### GENERAL
MENU_DESCRIPTION = "\n\nCписок доступных команд:\n/start — Главное меню\n/info — Справка\n/feedback — Оставить отзыв"


#### REPLIES (FOR CHATBOT)
INDIVIDUAL_TYPE_REPLY = 'Один'
TEAM_TYPE_REPLY = 'С коллегами'

HIGH_FREQUENCY_REPLY = 'Два и более раз в неделю 🐆'
MEDIUM_FREQUENCY_REPLY = 'Раз в неделю 🐇'
LOW_FREQUENCY_REPLY = 'Раз в две недели 🐢'

MALE_REPLY = 'Мужчина'
FEMALE_REPLY = 'Женщина'

DATING_REASON_REPLY = 'Найти вторую половину ❤'
NETWORKING_REASON_REPLY = 'Поговорить о работе'
HAVING_FUN_REASON_REPLY = 'Просто отдохнуть'

NO_TIME_REPLY = 'Вряд ли найду время'
NOT_IN_MOOD_REPLY = 'Не в настроении'
NO_INTEREST_REPLY = 'Что-то неинтересно...'

HAVENT_CONTACTED_REPLY = 'Партнер не вышел на связь'
COULDNT_ARRANGE_REPLY = 'Не смогли договориться когда/где'
FORCED_MAJOR_REPLY = 'Форс-мажор'

POSITIVE_REPLY = "Да"
NEGATIVE_REPLY = "Нет"


##### CHOICES (REPLIES MAP FOR DATABASE)
INDIVIDUAL = 'I'
TEAM = 'T'

USER_TYPE_CHOICES = [
    (INDIVIDUAL, INDIVIDUAL_TYPE_REPLY),
   (TEAM, TEAM_TYPE_REPLY)
]


HIGH = 'H'
MEDIUM = 'M'
LOW = 'L'

MEETING_FREQUENCY_CHOICES = [
    (HIGH, HIGH_FREQUENCY_REPLY),
    (MEDIUM, MEDIUM_FREQUENCY_REPLY),
    (LOW, LOW_FREQUENCY_REPLY),
]


DATING = 'D'
NETWORKING = 'N'
HAVING_FUN = 'HF'

MOTITVATION_CHOICES = [
    (DATING, DATING_REASON_REPLY),
    (NETWORKING, NETWORKING_REASON_REPLY),
    (HAVING_FUN, HAVING_FUN_REASON_REPLY),
]


MALE = 'M'
FEMALE = 'F'

GENDER_CHOICES = [
    (MALE, MALE_REPLY),
    (FEMALE, FEMALE_REPLY)
]


NO_TIME = 'NT'
NOT_IN_MOOD = 'NIM'
NO_INTEREST = 'NI'

CANCELLATION_REASON_CHOICES = [
    ('', '-'),
    (NO_TIME, NO_TIME_REPLY),
    (NOT_IN_MOOD, NOT_IN_MOOD_REPLY),
    (NO_INTEREST, NO_INTEREST_REPLY)
]


HAVENT_CONTACTED = 'DC'
COULDNT_ARRANGE = 'CA'
FORCED_MAJOR = 'FM'

ARRANGEMENT_FAILURE_REASONS = [
    ('', '-'),
    (HAVENT_CONTACTED, HAVENT_CONTACTED_REPLY),
    (COULDNT_ARRANGE, COULDNT_ARRANGE_REPLY),
    (FORCED_MAJOR, FORCED_MAJOR_REPLY)
]
