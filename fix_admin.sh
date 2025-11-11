#!/bin/bash
# Одна команда чтобы зафиксить админку

cd ~/shoesbot
git pull origin main
cd shoessite
source ../.venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart shoesdjango.service nginx
echo "✅ Готово! Обнови https://pochtoy.us/admin/"

