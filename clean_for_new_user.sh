#!/bin/bash
# Скрипт очистки проекта для передачи новому пользователю

echo "🧹 Очистка проекта ShoesBot..."

cd "$(dirname "$0")"

# 1. Удаляем .env (содержит секретные ключи)
if [ -f .env ]; then
    echo "✅ Создаю .env.example..."
    cat > .env.example << 'EOF'
# Обязательные ключи
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=sk-proj-your_key_here

# Опциональные (для одежды)
FASHN_API_KEY=fa-your_key_here

# Опциональные (улучшают распознавание)
GOOGLE_VISION_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=

# Буферный бот
BUFFER_BOT_TOKEN=

# Интеграция со складом
POCHTOY_API_URL=
POCHTOY_API_TOKEN=

# Cloudflared (автоматически)
CLOUDFLARED_URL=
EOF
    echo "⚠️  Удаляю .env (содержит ваши секретные ключи)"
    rm .env
fi

# 2. Очищаем БД
echo "🗑️  Очищаю базу данных..."
cd shoessite
rm -f db.sqlite3
python manage.py migrate --noinput 2>/dev/null
cd ..

# 3. Удаляем все фото
# ⚠️ ВНИМАНИЕ: Это удалит ВСЕ фотки! Используйте только для передачи проекта новому пользователю!
read -p "⚠️  Вы уверены что хотите удалить ВСЕ фотки? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Отменено. Фотки не удалены."
    exit 1
fi
echo "📸 Удаляю тестовые фото..."
rm -rf shoessite/media/photos/*
rm -rf shoessite/media/buffer/*
mkdir -p shoessite/media/photos
mkdir -p shoessite/media/buffer

# 4. Удаляем логи
echo "📋 Удаляю логи..."
rm -f bot.log
rm -f /tmp/fashn_*.log
rm -f /tmp/cloudflared.log
rm -f /tmp/buffer_bot.log

# 5. Удаляем кэш Python
echo "🗂️  Удаляю кэш..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# 6. Удаляем виртуальное окружение (пользователь создаст свое)
echo "🐍 Удаляю виртуальное окружение..."
rm -rf .venv

echo ""
echo "✅ Готово! Проект очищен для нового пользователя."
echo ""
echo "Новому пользователю нужно:"
echo "1. Скопировать .env.example в .env"
echo "2. Заполнить API ключи в .env"
echo "3. Создать виртуальное окружение: python3 -m venv .venv"
echo "4. Установить зависимости: pip install -r requirements.txt"
echo "5. Следовать SETUP_GUIDE.md"

