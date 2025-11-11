#!/bin/sh
python /app/shoessite/manage.py migrate
gunicorn --chdir /app/shoessite shoessite.wsgi:application --bind 0.0.0.0:$PORT
