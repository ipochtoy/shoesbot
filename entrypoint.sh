#!/bin/bash
set -e

echo "Starting entrypoint script..."
cd /app/shoessite

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn shoessite.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4

