#!/bin/bash
# Скрипт автоматического деплоя на VM

set -e

echo "🚀 Деплой shoesbot..."

cd ~/shoesbot

STATUS=$(git status -sb)
DIRTY=$(git status --porcelain)
if [ -n "$DIRTY" ]; then
  echo "⚠️  Есть незакоммиченные изменения. Сначала commit/push, потом запуск deploy."
  exit 1
fi

if echo "$STATUS" | grep -q "ahead"; then
  echo "⚠️  Репозиторий содержит локальные коммиты, пропускаю git pull (чтобы не потерять изменения)"
else
  echo "📥 Загружаю изменения из GitHub..."
  git pull origin main
fi

echo "🎨 Собираю статику..."
cd shoessite
source ../.venv/bin/activate
python manage.py collectstatic --noinput

echo "🔄 Перезапускаю сервисы..."
sudo systemctl restart shoesdjango.service
sudo systemctl restart shoesbot.service

echo "✅ Деплой завершен!"
echo ""
echo "Проверь:"
echo "  - Админка: https://pochtoy.us/admin/"
echo "  - Бот работает: /ping в Telegram"
