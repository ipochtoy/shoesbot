#!/bin/bash
# Безопасный деплой с автотестами, бекапом и откатом

set -e

echo "🚀 Starting deployment..."
cd /home/pochtoy/shoesbot

# Создаем бекап БД перед деплоем
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /home/pochtoy/backups/critical
cp shoessite/db.sqlite3 /home/pochtoy/backups/critical/pre-deploy-${DATE}.sqlite3
echo "✅ Backup created: pre-deploy-${DATE}.sqlite3"

# Сохраняем текущий коммит для возможного отката
PREVIOUS_COMMIT=$(git rev-parse HEAD)
echo "📌 Previous commit: $PREVIOUS_COMMIT"

# Проверяем незакоммиченные изменения
DIRTY=$(git status --porcelain)
if [ -n "$DIRTY" ]; then
    echo "⚠️  Незакоммиченные изменения. Сохраняю в stash..."
    git stash
fi

# Загружаем изменения
echo "📥 Pulling from GitHub..."
git pull origin main

# Устанавливаем зависимости
echo "📚 Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

# Запускаем миграции
echo "🗃️  Running migrations..."
cd shoessite
../.venv/bin/python manage.py migrate --noinput

# Собираем статику
echo "🎨 Collecting static files..."
../.venv/bin/python manage.py collectstatic --noinput
cd ..

# Фиксируем права доступа для nginx
echo "🔒 Fixing static permissions..."
bash fix_static_permissions.sh

# Перезапускаем Django (бот НЕ трогаем - священная корова!)
echo "🔄 Restarting Django..."
sudo systemctl restart shoesdjango.service
sleep 5

# Health check
echo "🏥 Health check..."
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/ || echo '000')
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo "❌ HEALTH CHECK FAILED (HTTP $HTTP_CODE)"
    echo "🔙 Rolling back..."
    sudo systemctl stop shoesdjango.service
    git reset --hard $PREVIOUS_COMMIT
    cp /home/pochtoy/backups/critical/pre-deploy-${DATE}.sqlite3 shoessite/db.sqlite3
    sudo systemctl start shoesdjango.service
    echo "❌ Deployment failed and rolled back"
    exit 1
fi

echo ""
echo "✅ Deployment successful!"
echo "📝 Deployed: $(git rev-parse --short HEAD)"
echo ""
echo "Проверь:"
echo "  - Админка: https://pochtoy.us/admin/"
echo "  - Бот работает: /ping в Telegram"
