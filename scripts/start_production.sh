#!/usr/bin/env bash
export RANDOM_COFFEE_SETTINGS=production
. ../venv/bin/activate
nohup python manage.py runserver 127.0.0.1:8081 --noreload > server.log 2>&1 & echo $! >> pids &
deactivate