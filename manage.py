#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'random_coffee_platform.settings.common')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    sys_argv_custom =  sys.argv
    sys_argv_custom[0] = 'manage.py'
    execute_from_command_line(sys_argv_custom)


if __name__ == '__main__':
    main()
