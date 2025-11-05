web: python shoessite/manage.py migrate && python shoessite/manage.py collectstatic --noinput && cd shoessite && gunicorn shoessite.wsgi:application --bind 0.0.0.0:$PORT

