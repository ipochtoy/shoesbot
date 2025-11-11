#!/bin/bash
# Скрипт автоматического деплоя на VM

echo "🚀 Деплой shoesbot..."

# Переходим в папку проекта
cd ~/shoesbot

# Получаем последние изменения из GitHub
echo "📥 Загружаю изменения из GitHub..."
git pull origin main

# Собираем статику Django
echo "🎨 Собираю статику..."
cd shoessite
source ../.venv/bin/activate
python manage.py collectstatic --noinput

# Перезапускаем сервисы
echo "🔄 Перезапускаю сервисы..."
sudo systemctl restart shoesdjango.service
sudo systemctl restart shoesbot.service

echo "✅ Деплой завершен!"
echo ""
echo "Проверь:"
echo "  - Админка: https://pochtoy.us/admin/"
echo "  - Бот работает: /ping в Telegram"

