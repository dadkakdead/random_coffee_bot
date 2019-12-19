#!/usr/bin/env bash
. ~/random_coffee_platform/venv/bin/activate
export RANDOM_COFFEE_SETTINGS=production
python ~/random_coffee_platform/manage.py collect_feedback --username random_coffee_starthub_bot
deactivate
