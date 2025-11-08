#!/bin/bash
# Создает архив проекта для передачи другу (без ключей и данных)

cd "$(dirname "$0")"

PACKAGE_NAME="watchbot_package_$(date +%Y%m%d).zip"

echo "📦 Создаю пакет для передачи..."

# 1. Создаем временную директорию
TEMP_DIR="/tmp/watchbot_clean"
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# 2. Копируем весь проект
echo "📋 Копирую файлы..."
rsync -av --exclude='.git' \
          --exclude='.venv' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.env' \
          --exclude='db.sqlite3' \
          --exclude='media/photos' \
          --exclude='media/buffer' \
          --exclude='*.log' \
          --exclude='.cursor' \
          . $TEMP_DIR/

# 3. Создаем .env.example
echo "🔑 Создаю .env.example..."
cat > $TEMP_DIR/.env.example << 'EOF'
# ============================================
# ОБЯЗАТЕЛЬНЫЕ КЛЮЧИ
# ============================================

# Telegram бот (@BotFather)
BOT_TOKEN=

# OpenAI для AI описаний ($5 бонус при регистрации)
OPENAI_API_KEY=

# ============================================
# ОПЦИОНАЛЬНЫЕ КЛЮЧИ (можно пропустить)
# ============================================

# FASHN AI - только для одежды! Для часов НЕ НУЖЕН
FASHN_API_KEY=

# Google Vision - улучшает распознавание текста
GOOGLE_VISION_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=

# Буферный бот (если нужна сортировка 50+ фото)
BUFFER_BOT_TOKEN=

# Твой склад API (опционально)
POCHTOY_API_URL=
POCHTOY_API_TOKEN=

# Cloudflared (заполнится автоматически)
CLOUDFLARED_URL=
EOF

# 4. Очищаем БД и создаем пустую
echo "🗄️  Создаю чистую БД..."
cd $TEMP_DIR/shoessite
rm -f db.sqlite3
python3 -m venv temp_venv
source temp_venv/bin/activate
pip install django pillow -q
python manage.py migrate --noinput 2>/dev/null
rm -rf temp_venv
cd ..

# 5. Создаем структуру media папок
mkdir -p shoessite/media/photos
mkdir -p shoessite/media/buffer
echo "Папка для фото" > shoessite/media/photos/.gitkeep
echo "Папка для буфера" > shoessite/media/buffer/.gitkeep

# 6. Создаем архив
cd /tmp
echo "📦 Создаю ZIP архив..."
zip -r $PACKAGE_NAME watchbot_clean/ -q

# 7. Перемещаем в исходную директорию
mv $PACKAGE_NAME ~/Desktop/
echo ""
echo "✅ Готово!"
echo ""
echo "📦 Архив создан: ~/Desktop/$PACKAGE_NAME"
echo "📄 Размер: $(du -sh ~/Desktop/$PACKAGE_NAME | cut -f1)"
echo ""
echo "Отправь другу этот файл + файл SIMPLE_SETUP.pdf"
echo ""

# Очищаем
rm -rf $TEMP_DIR

