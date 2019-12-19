#### Описание
Телеграм-бот для организации встреч Random Coffee.

#### Настройка бота
Через @BotFather

Бот должен уметь принимать 3 команды:
```text
start -  Главное меню / Профиль
info - Справка
feedback - Оставить отзыв
```

+1 команда для бота, используеющегося в разработке:
```
status - Состояние диалога
```

#### Управление

##### Запуск бота на сервере (режим WEBHOOK)
```bash
./start_production.sh
```

##### Запуск бота локально (режим POLLING) с доступом к интерфейсу администратора

```bash
./start_development.sh
```

#### CRON на сервере
```txt
# MOSCOW LOCAL TIME IS +3h RELATIVE TO SYSTEM TIME
# m h  dom mon dow   command
0 9 * * THU ~/random_coffee_platform/scripts/send_invitations_prod.sh
0 9 * * MON ~/random_coffee_platform/scripts/connect_participants_prod.sh
0 15 * * FRI ~/random_coffee_platform/scripts/collect_feedback_prod.sh
```

#### База данных
##### Открыть базу данных и пошариться по ней
SQLite. 1 file = 1 database.

Подключиться к базе:
```bash
sqlite3 random_coffee_platform/db.sqlite3
```

Показать таблицы
```sqlite-psql
.tables
```

Посмотреть число пользователей в базе:
```sqlite-psql
SELECT COUNT(*) FROM connector_user;
```

Выйти из базы: **Ctrl+D**.

#### Заметки
1. Пошарить контакт, не зная его телефон, нельзя - API потребует указания обоих полей.
1. Телефоны для фейковых Телеграм-аккаунтов можно взять тут: https://sms-activate.ru/ru/
1. Django-обвязка во многом перенята у https://github.com/jlmadurga/django-telegram-bot
1. Чтобы что-то вывести в лог, использовать logger.info() / logger.error()
1. Все состояния бота пишутся в стиле CamelCase и заканчиваются на State, перечислены в chatbot.py
1. Чтобы создать пользователя вручную, нужно обязательно создать оба объекта User и UserState
1. Забаненным пользователь (enabled=False в User) больше не рассылаются приглашения
1. Так как в России Телеграм забанен, запускаем его локально в режиме polling и берем прокси у Proxymesh https://www.proxymesh.com/
1. Создание SSL сертификата для получение сообщений по webhook'ам: https://www.digitalocean.com/community/tutorials/how-to-create-an-ssl-certificate-on-nginx-for-ubuntu-14-04

#### Хотелки
1. Мотивация встречи - должно быть multiple choice поле
1. Добавить выбор темы встречи - прикольно @MRRandomCoffeeBot, но там быстро образуется бардак
1. В профиле нужно добавить кнопку "Отказаться от встречи на этой неделе"
1. Показывать иконку "печатает" в боте после получения сообщения от пользователя (https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets, Send chat action)
1. Отправлять не только телефон, но и телеграмный username в составе описания встречи (чтобы клинкул и перешел)
1. Добавить список разрешенных/запрещенных пользователей
1. Вынести настройки системы в админку Django
1. Добавить функцию "Рассылка новостного сообщения"
1. Переставить местами строки в профиле, чтобы номера строк соответствовали номерам вопросов
1. Локализация - чтобы можно было выбирать язык интерфейса.

#### Проблемки
1. Рефакторинг: chatbot.py все еще использует переменные из vars.py, но не все;
1. Тесты: код прошел только ручное тестирование, unit тесты не написаны
1. Все, что отмечен в коде метками TODO

#### Настройки NGINX
```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    location / {
        proxy_pass http://localhost:8081;
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
    }
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen              443 ssl;
    server_name         example.com;
    ssl_certificate     /home/admin/cert.pem;
    ssl_certificate_key /home/admin/pkey.key;

    location /<BOT_TOKEN> {
        proxy_pass http://127.0.0.1:8081;
    }

    location /<BOT_TOKEN> {
        proxy_pass http://127.0.0.1:8081;
    }

}
```
