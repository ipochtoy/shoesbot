# Setup & Installation Guide

Пошаговая инструкция по установке и настройке ShoesBot.

## 📋 Требования

### Системные Требования
- **OS**: Linux, macOS, или Windows (с WSL)
- **Python**: 3.9 или выше
- **RAM**: Минимум 2GB (рекомендуется 4GB для AI операций)
- **Disk**: 5GB+ свободного места

### Python Dependencies
- Django 4.2+
- python-telegram-bot
- Pillow (PIL)
- pyzbar
- opencv-python
- requests
- openai

### External API Keys (Обязательно)
- ✅ **Telegram Bot Token** - [@BotFather](https://t.me/botfather)
- ✅ **OpenAI API Key** - [platform.openai.com](https://platform.openai.com/)
- ✅ **FASHN API Key** - [fashn.ai](https://fashn.ai/)
- ⚠️ **eBay App ID** - [developer.ebay.com](https://developer.ebay.com/) (опционально для поиска)
- ⚠️ **Google Cloud Vision** - [cloud.google.com](https://cloud.google.com/) (опционально для OCR)

## 🚀 Установка

### Шаг 1: Клонирование Репозитория

```bash
# Клонируем проект
git clone https://github.com/your-org/shoesbot.git
cd shoesbot
```

### Шаг 2: Создание Виртуального Окружения

```bash
# Создаем venv
python3 -m venv venv

# Активируем (Linux/macOS)
source venv/bin/activate

# Активируем (Windows)
venv\Scripts\activate
```

### Шаг 3: Установка Зависимостей

```bash
# Устанавливаем все зависимости
pip install -r requirements.txt
```

**Если возникают проблемы с pyzbar:**

```bash
# macOS
brew install zbar

# Ubuntu/Debian
sudo apt-get install libzbar0

# Windows
# Скачайте pre-built wheels: https://github.com/NaturalHistoryMuseum/pyzbar/#installation
```

### Шаг 4: Настройка Переменных Окружения

Создайте файл `.env` в корне проекта:

```bash
# Копируем пример (если есть)
cp .env.example .env

# Или создаем новый
nano .env
```

**Содержимое `.env`:**

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
BACKEND_URL=http://localhost:8000

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o

# FASHN AI
FASHN_API_KEY=your-fashn-api-key-here

# eBay (опционально)
EBAY_APP_ID=YourEbay-AppID-PRD-xxxxx

# Google Cloud Vision (опционально)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json

# Django
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=*
```

**⚠️ ВАЖНО**: Не добавляйте `.env` в git!

```bash
# Проверяем, что .env в .gitignore
echo ".env" >> .gitignore
```

### Шаг 5: Настройка Django

```bash
cd shoessite

# Создаем директорию для логов
mkdir -p logs

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя (опционально)
python manage.py createsuperuser

# Собираем статику (для production)
python manage.py collectstatic --noinput
```

### Шаг 6: Настройка Telegram Bot

```bash
cd ../shoesbot

# Проверяем, что env_setup.py правильно настроен
python -c "import shoesbot.env_setup; print('Environment setup OK')"
```

## ▶️ Запуск

### Development Mode

**Терминал 1 - Django Server:**

```bash
cd shoessite
python manage.py runserver
```

Приложение доступно: http://localhost:8000

**Терминал 2 - Telegram Bot:**

```bash
cd shoesbot
python telegram_bot.py
```

Bot запущен и принимает сообщения!

### Проверка Работоспособности

1. **Проверка Django:**
   ```bash
   curl http://localhost:8000/photos/api/get-last-card/
   ```
   Ожидается JSON ответ (может быть пустой массив).

2. **Проверка Telegram Bot:**
   - Откройте Telegram
   - Найдите вашего бота (@your_bot_name)
   - Отправьте команду `/start`
   - Ожидается приветственное сообщение

3. **Проверка Barcode Detection:**
   - Отправьте боту фото с баркодом
   - Бот должен распознать баркод
   - Проверьте веб-интерфейс: http://localhost:8000/photos/sorting/

## 🔧 Конфигурация

### Django Settings (`shoessite/shoessite/settings.py`)

**Debug Mode:**
```python
# Development
DEBUG = True

# Production
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
```

**Database:**
```python
# Development (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Production (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shoesbot_db',
        'USER': 'shoesbot_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**Logging Levels:**
```python
LOGGING = {
    # ...
    'loggers': {
        'photos': {
            'level': 'DEBUG' if DEBUG else 'INFO',  # Adjust as needed
        },
    },
}
```

### Bot Configuration (`shoesbot/config.py`)

```python
@dataclass
class BotConfig:
    # Таймауты буферизации
    BUFFER_TIMEOUT: Final[float] = 3.0  # Ждать фото 3 секунды
    BUFFER_WAIT_TIME: Final[float] = 3.2

    # Retry логика
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAYS: Final[tuple] = (0.5, 1.0, 2.0)

    # Memory cleanup
    PENDING_TTL_HOURS: Final[int] = 24  # Чистить после 24 часов
    SENT_BATCHES_TTL_HOURS: Final[int] = 48
```

### Barcode Decoders (`shoesbot/pipeline.py`)

```python
# Быстрые декодеры (всегда включены)
fast_decoders = [
    ZBarDecoder(),     # EAN13, QR, CODE128, etc
    CVQRDecoder(),     # OpenCV QR detection
]

# Медленные декодеры (только если быстрые не нашли)
slow_decoders = [
    ImprovedGGLabelDecoder(),  # Yellow GG+Q labels
]

# Emergency декодеры (только если все провалились)
emergency_decoders = [
    OpenAIDecoder(),  # Дорого! Только в крайнем случае
]
```

## 🗄️ База Данных

### SQLite (Development)

Уже настроена по умолчанию. Файл: `shoessite/db.sqlite3`

**Backup:**
```bash
cp shoessite/db.sqlite3 shoessite/db.sqlite3.backup
```

### PostgreSQL (Production)

**Установка PostgreSQL:**

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql
```

**Создание базы:**

```sql
-- Подключаемся к PostgreSQL
sudo -u postgres psql

-- Создаем базу и пользователя
CREATE DATABASE shoesbot_db;
CREATE USER shoesbot_user WITH PASSWORD 'secure_password';
ALTER ROLE shoesbot_user SET client_encoding TO 'utf8';
ALTER ROLE shoesbot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE shoesbot_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE shoesbot_db TO shoesbot_user;
\q
```

**Обновление settings.py:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shoesbot_db',
        'USER': 'shoesbot_user',
        'PASSWORD': os.getenv('DB_PASSWORD', 'secure_password'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**Миграция данных:**

```bash
# Экспорт из SQLite
python manage.py dumpdata > data.json

# Изменить settings.py на PostgreSQL

# Импорт в PostgreSQL
python manage.py migrate
python manage.py loaddata data.json
```

## 📦 Deployment

### systemd Service (Linux)

**Django Service** (`/etc/systemd/system/shoesbot-django.service`):

```ini
[Unit]
Description=ShoesBot Django Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/shoesbot/shoessite
Environment="PATH=/var/www/shoesbot/venv/bin"
EnvironmentFile=/var/www/shoesbot/.env
ExecStart=/var/www/shoesbot/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    shoessite.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Telegram Bot Service** (`/etc/systemd/system/shoesbot-telegram.service`):

```ini
[Unit]
Description=ShoesBot Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/shoesbot/shoesbot
Environment="PATH=/var/www/shoesbot/venv/bin"
EnvironmentFile=/var/www/shoesbot/.env
ExecStart=/var/www/shoesbot/venv/bin/python telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Запуск:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable shoesbot-django shoesbot-telegram
sudo systemctl start shoesbot-django shoesbot-telegram

# Check status
sudo systemctl status shoesbot-django
sudo systemctl status shoesbot-telegram
```

### Nginx Configuration

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Static files
    location /static/ {
        alias /var/www/shoesbot/shoessite/static/;
    }

    # Media files
    location /media/ {
        alias /var/www/shoesbot/shoessite/media/;
    }

    # Proxy to Django
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**SSL with Let's Encrypt:**

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔍 Проверка Установки

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "=== ShoesBot Health Check ==="

# Check Django
echo -n "Django: "
curl -s http://localhost:8000/photos/api/get-last-card/ > /dev/null && echo "✓ OK" || echo "✗ FAIL"

# Check Database
echo -n "Database: "
cd shoessite && python manage.py migrate --check > /dev/null 2>&1 && echo "✓ OK" || echo "✗ FAIL"

# Check Telegram Bot
echo -n "Bot Process: "
pgrep -f telegram_bot.py > /dev/null && echo "✓ OK" || echo "✗ FAIL"

# Check API Keys
echo -n "OpenAI Key: "
[ ! -z "$OPENAI_API_KEY" ] && echo "✓ Set" || echo "✗ Not Set"

echo -n "FASHN Key: "
[ ! -z "$FASHN_API_KEY" ] && echo "✓ Set" || echo "✗ Not Set"

echo -n "Telegram Token: "
[ ! -z "$TELEGRAM_BOT_TOKEN" ] && echo "✓ Set" || echo "✗ Not Set"

echo "=== End Health Check ==="
```

**Запуск:**
```bash
chmod +x health_check.sh
./health_check.sh
```

## 🐛 Troubleshooting

Если что-то не работает, см. [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Быстрые Решения

**Django не запускается:**
```bash
# Проверить порт
lsof -i :8000

# Проверить миграции
python manage.py migrate --check

# Проверить логи
tail -f shoessite/logs/errors.log
```

**Bot не отвечает:**
```bash
# Проверить токен
python -c "import os; print('Token:', os.getenv('TELEGRAM_BOT_TOKEN'))"

# Проверить сеть
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Проверить логи
tail -f shoesbot/telegram_bot.log
```

**Barcode не распознается:**
```bash
# Проверить pyzbar
python -c "from pyzbar import pyzbar; print('pyzbar OK')"

# Проверить OpenCV
python -c "import cv2; print('OpenCV version:', cv2.__version__)"

# Тест pipeline
cd shoesbot
python process_single_photo.py <path-to-image>
```

## 📚 Следующие Шаги

1. ✅ Прочитать [ARCHITECTURE.md](ARCHITECTURE.md) - понять структуру
2. ✅ Прочитать [API.md](API.md) - изучить endpoints
3. ✅ Настроить мониторинг логов
4. ✅ Протестировать основные функции
5. ✅ Создать резервные копии базы данных

## 🔄 Обновление

```bash
# Backup базы данных
cp shoessite/db.sqlite3 shoessite/db.sqlite3.backup

# Pull изменений
git pull origin main

# Обновить зависимости
pip install -r requirements.txt --upgrade

# Применить миграции
cd shoessite
python manage.py migrate

# Restart services
sudo systemctl restart shoesbot-django shoesbot-telegram
```

---

**Need Help?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue on GitHub.
