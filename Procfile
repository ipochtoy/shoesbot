web: cd shoessite && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn shoessite.wsgi:application --bind 0.0.0.0:$PORT
bot: DYLD_LIBRARY_PATH=/opt/homebrew/lib python shoesbot/telegram_bot.py

