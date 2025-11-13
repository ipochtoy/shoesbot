#!/bin/bash
# Collect static files and restart Django production service
set -e

echo '🛑 Останавливаю все Django процессы на dev порту...'
pkill -9 -f 'manage.py runserver' || true

echo '🎨 Собираю статические файлы...'
cd /home/pochtoy/shoesbot/shoessite
/home/pochtoy/shoesbot/.venv/bin/python manage.py collectstatic --noinput

echo '🔄 Перезапускаю Django production сервис...'
sudo systemctl restart shoesdjango.service

echo '⏳ Ждем 3 секунды...'
sleep 3

echo '📊 Статус Django сервиса:'
sudo systemctl status shoesdjango.service --no-pager

echo ''
echo '✅ Django перезапущен и статика собрана'
