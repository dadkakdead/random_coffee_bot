#!/usr/bin/env bash
export RANDOM_COFFEE_SETTINGS=development
. ../venv/bin/activate
python manage.py runserver --noreload > server.log 2>&1 & echo $! >> pids &
python manage.py start_polling --username=random_coffee_development_bot > polling.log 2>&1 & echo $! >> pids &
deactivate