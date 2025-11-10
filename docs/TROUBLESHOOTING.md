# Troubleshooting Guide

Решения частых проблем и ошибок в ShoesBot.

## 📋 Общая Диагностика

### Быстрая Проверка Системы

```bash
# 1. Проверка Django
curl http://localhost:8000/photos/api/get-last-card/
# Ожидается: JSON ответ

# 2. Проверка базы данных
cd shoessite && python manage.py migrate --check
# Ожидается: "No migrations to apply"

# 3. Проверка Telegram bot
pgrep -f telegram_bot.py
# Ожидается: process ID

# 4. Проверка логов
tail -f shoessite/logs/errors.log
```

### Где Искать Логи

```
shoessite/logs/
├── errors.log          # Все ошибки (уровень ERROR)
├── requests.log        # HTTP запросы (уровень INFO)
└── performance.log     # Медленные запросы >2s (уровень WARNING)
```

**Полезные команды:**

```bash
# Последние 50 ошибок
tail -50 shoessite/logs/errors.log

# Следить за ошибками в реальном времени
tail -f shoessite/logs/errors.log

# Медленные запросы
grep "SLOW REQUEST" shoessite/logs/performance.log

# Поиск конкретной ошибки
grep -i "openai" shoessite/logs/errors.log
```

## 🔴 Django Проблемы

### Проблема: Django не запускается

**Симптомы:**
```
Error: That port is already in use.
```

**Решение:**

```bash
# Найти процесс на порту 8000
lsof -i :8000

# Убить процесс
kill -9 <PID>

# Или запустить на другом порту
python manage.py runserver 8001
```

---

**Симптомы:**
```
django.db.utils.OperationalError: no such table: photos_photobatch
```

**Решение:**

```bash
# Применить миграции
cd shoessite
python manage.py migrate

# Если не помогло, пересоздать базу
rm db.sqlite3
python manage.py migrate
```

---

**Симптомы:**
```
ModuleNotFoundError: No module named 'photos.middleware'
```

**Решение:**

```bash
# Проверить, что файлы middleware существуют
ls -la shoessite/photos/middleware/

# Если отсутствуют __init__.py
touch shoessite/photos/middleware/__init__.py

# Перезапустить Django
python manage.py runserver
```

### Проблема: 500 Internal Server Error

**Диагностика:**

```bash
# Включить DEBUG режим
# В settings.py:
DEBUG = True

# Перезапустить
python manage.py runserver

# Посмотреть traceback в браузере или логах
tail -f shoessite/logs/errors.log
```

**Частые причины:**

1. **Отсутствующие environment variables**
   ```bash
   # Проверить .env файл
   cat .env | grep OPENAI_API_KEY
   ```

2. **Неправильные права на файлы**
   ```bash
   # Дать права на media и logs
   chmod -R 755 shoessite/media
   chmod -R 755 shoessite/logs
   ```

3. **База данных заблокирована**
   ```bash
   # SQLite locked error
   # Закрыть все подключения и перезапустить
   ```

### Проблема: Static files не загружаются

**Решение:**

```bash
# Собрать статику
cd shoessite
python manage.py collectstatic --noinput

# Проверить настройки
python manage.py findstatic photos/js/api.js

# Development: убедиться что DEBUG=True
# Production: настроить Nginx для /static/
```

## 🤖 Telegram Bot Проблемы

### Проблема: Bot не отвечает

**Диагностика:**

```bash
# 1. Проверить токен
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Token:', os.getenv('TELEGRAM_BOT_TOKEN'))"

# 2. Проверить соединение с Telegram API
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 3. Проверить процесс
ps aux | grep telegram_bot
```

**Решение:**

```bash
# Если токен неправильный
nano .env  # Исправить TELEGRAM_BOT_TOKEN

# Если процесс не запущен
cd shoesbot
python telegram_bot.py
```

---

**Симптомы:**
```
telegram.error.Conflict: Conflict: terminated by other getUpdates request
```

**Причина:** Bot уже запущен в другом месте.

**Решение:**

```bash
# Найти все процессы
ps aux | grep telegram_bot

# Убить старые процессы
pkill -f telegram_bot.py

# Запустить заново
python telegram_bot.py
```

### Проблема: Bot получает фото, но не обрабатывает

**Диагностика:**

```bash
# Проверить логи бота
tail -f shoesbot/telegram_bot.log

# Проверить, что Django доступен
curl http://localhost:8000/photos/api/upload-batch/

# Проверить BACKEND_URL в .env
grep BACKEND_URL .env
```

**Решение:**

```bash
# Убедиться, что Django запущен
cd shoessite && python manage.py runserver

# Проверить BACKEND_URL
# В .env должно быть:
BACKEND_URL=http://localhost:8000

# Перезапустить бота
cd shoesbot && python telegram_bot.py
```

### Проблема: Баркоды не распознаются

**Диагностика:**

```bash
# Тест pyzbar
python -c "from pyzbar import pyzbar; print('pyzbar OK')"

# Тест OpenCV
python -c "import cv2; print('OpenCV:', cv2.__version__)"

# Тест одного фото
cd shoesbot
python process_single_photo.py /path/to/test/image.jpg
```

**Решение для pyzbar:**

```bash
# macOS
brew install zbar
pip install pyzbar

# Ubuntu/Debian
sudo apt-get install libzbar0
pip install pyzbar

# Windows
pip install pyzbar-windows
```

**Решение для OpenCV:**

```bash
pip install opencv-python-headless
```

### Проблема: GG+Q лейблы не читаются

**Симптомы:** Бот находит либо GG текст, либо Q баркод, но не оба.

**Решение:**

```bash
# Проверить, что используется ImprovedGGLabelDecoder
grep "ImprovedGGLabelDecoder" shoesbot/pipeline.py

# Должно быть:
# slow_decoders = [ImprovedGGLabelDecoder()]

# Проверить, что OpenAI emergency включен
grep "emergency_decoders" shoesbot/pipeline.py
```

**Если все еще не работает:**

1. Проверить качество фото (должно быть четким)
2. Проверить OPENAI_API_KEY в .env
3. Проверить баланс OpenAI аккаунта

## 🎨 Frontend Проблемы

### Проблема: JavaScript ошибки в консоли

**Диагностика:**

```javascript
// Открыть DevTools (F12) -> Console
// Проверить ошибки
```

**Частые ошибки:**

1. **Alpine is not defined**
   ```html
   <!-- Проверить, что base_scripts.html подключен -->
   {% include 'photos/base_scripts.html' %}
   ```

2. **Axios is not defined**
   ```html
   <!-- Проверить CDN ссылки -->
   <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
   ```

3. **API.someMethod is not a function**
   ```html
   <!-- Проверить, что api.js загружен -->
   <script src="{% static 'photos/js/api.js' %}"></script>
   ```

### Проблема: AJAX запросы не работают

**Симптомы:** Кнопки не работают, данные не сохраняются.

**Диагностика:**

```javascript
// DevTools -> Network tab
// Проверить HTTP запросы и ответы
```

**Решение:**

```javascript
// Проверить Axios timeout
// В base_scripts.html:
axios.defaults.timeout = 150000; // 150 секунд для FASHN

// Проверить CSRF токен
console.log(document.querySelector('[name=csrfmiddlewaretoken]').value);
```

## 🔌 API Integration Проблемы

### Проблема: OpenAI API ошибки

**Симптомы:**
```
openai.error.RateLimitError: Rate limit exceeded
```

**Решение:**
- Проверить лимиты: https://platform.openai.com/account/limits
- Подождать минуту и повторить
- Upgrade план если нужно

---

**Симптомы:**
```
openai.error.AuthenticationError: Invalid API key
```

**Решение:**

```bash
# Проверить ключ
grep OPENAI_API_KEY .env

# Получить новый ключ
# https://platform.openai.com/api-keys

# Обновить .env и перезапустить
```

---

**Симптомы:**
```
openai.error.InvalidRequestError: This model's maximum context length is 128000 tokens
```

**Решение:**
- Уменьшить количество фотографий
- Сжать изображения перед отправкой
- Использовать меньше примеров в промпте

### Проблема: FASHN AI ошибки

**Симптомы:**
```
{"error": "Prediction failed"}
```

**Диагностика:**

```bash
# Проверить API key
grep FASHN_API_KEY .env

# Проверить логи
grep "FASHN" shoessite/logs/errors.log

# Тест API напрямую
curl -X POST https://api.fashn.ai/v1/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Решение:**
- Проверить лимиты (free tier = ~100 requests/day)
- Проверить формат изображения (должен быть JPEG/PNG)
- Проверить размер (<10MB)

---

**Симптомы:** Запрос зависает на 2+ минуты

**Это нормально!** FASHN обработка занимает 30-120 секунд.

**Решение:**

```javascript
// Увеличить timeout в base_scripts.html
axios.defaults.timeout = 180000; // 3 минуты
```

### Проблема: eBay Search не работает

**Симптомы:**
```
{"error": "eBay API error"}
```

**Решение:**

```bash
# Проверить APP ID
grep EBAY_APP_ID .env

# Получить новый APP ID
# https://developer.ebay.com/my/keys

# Проверить лимиты
# Standard = 5000 calls/day
```

## 💾 Database Проблемы

### Проблема: Database is locked

**Симптомы:**
```
sqlite3.OperationalError: database is locked
```

**Причина:** SQLite не поддерживает concurrent writes.

**Решение (Short-term):**

```bash
# Закрыть все подключения
pkill -f "python manage.py runserver"
pkill -f telegram_bot.py

# Restart
python manage.py runserver &
python telegram_bot.py &
```

**Решение (Long-term):**

Migrate to PostgreSQL (см. [SETUP.md](SETUP.md))

### Проблема: Миграции не применяются

**Симптомы:**
```
Your models have changes that are not yet reflected in a migration
```

**Решение:**

```bash
# Создать миграции
python manage.py makemigrations

# Применить
python manage.py migrate

# Проверить статус
python manage.py showmigrations
```

## 🖼️ Image Processing Проблемы

### Проблема: PIL/Pillow ошибки

**Симптомы:**
```
PIL.UnidentifiedImageError: cannot identify image file
```

**Решение:**

```bash
# Переустановить Pillow
pip uninstall Pillow
pip install Pillow

# Проверить формат файла
file /path/to/image.jpg

# Конвертировать в JPEG
convert input.png output.jpg
```

### Проблема: Images слишком большие

**Симптомы:** Slow uploads, API timeouts

**Решение:**

```python
# В shoessite/photos/services/image_service.py уже есть:
def resize_image(image, max_size=(1920, 1080)):
    """Resize image if too large."""
    # ...
```

**Manually:**

```bash
# ImageMagick
convert input.jpg -resize 1920x1080\> output.jpg

# Python
from PIL import Image
img = Image.open('input.jpg')
img.thumbnail((1920, 1080))
img.save('output.jpg', quality=85)
```

## 🔒 Permission Проблемы

### Проблема: Permission denied на файлах

**Симптомы:**
```
PermissionError: [Errno 13] Permission denied: '/path/to/media/...'
```

**Решение:**

```bash
# Дать права на директории
chmod -R 755 shoessite/media
chmod -R 755 shoessite/logs

# Или изменить владельца
chown -R $USER:$USER shoessite/media
chown -R $USER:$USER shoessite/logs
```

### Проблема: CSRF verification failed

**Симптомы:**
```
403 Forbidden - CSRF verification failed
```

**Решение для API endpoints:**

```python
# В views добавить декоратор
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def my_api_view(request):
    # ...
```

**Решение для форм:**

```html
<!-- В шаблоне -->
<form method="post">
    {% csrf_token %}
    <!-- ... -->
</form>
```

## 🌐 Network/Deployment Проблемы

### Проблема: Не могу подключиться к серверу

**Для локальной разработки:**

```bash
# Проверить, что Django слушает на правильном адресе
python manage.py runserver 0.0.0.0:8000

# Проверить ALLOWED_HOSTS
# В settings.py:
ALLOWED_HOSTS = ['*']  # Development only!
```

**Для production:**

```bash
# Проверить Nginx
sudo nginx -t
sudo systemctl status nginx

# Проверить firewall
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
```

### Проблема: Webhook не работает

**Диагностика:**

```bash
# Проверить endpoint доступен
curl -X POST http://localhost:8000/photos/api/pochtoy-webhook/ \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Проверить логи webhook
grep "webhook" shoessite/logs/requests.log
```

## 🧪 Testing & Debugging

### Debug Mode

```python
# В settings.py
DEBUG = True

# Включить Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### Interactive Shell

```bash
# Django shell
python manage.py shell

# Тест сервисов
from photos.services.ai_service import OpenAIService
ai = OpenAIService()
result = ai.generate_product_summary(['http://example.com/image.jpg'])
print(result)
```

### SQL Queries

```bash
# Посмотреть SQL запросы
python manage.py dbshell

# SQLite
.tables
.schema photos_photobatch
SELECT * FROM photos_photobatch LIMIT 10;
```

## 📞 Getting Help

### Checklist Before Asking

- [ ] Проверил логи (`logs/errors.log`)
- [ ] Проверил все environment variables
- [ ] Попробовал перезапустить Django и Bot
- [ ] Проверил версии зависимостей (`pip list`)
- [ ] Проверил, что миграции применены
- [ ] Прочитал эту документацию

### Информация для Bug Report

При создании issue, включите:

1. **Версия Python:** `python --version`
2. **Версия Django:** `python -m django --version`
3. **OS:** `uname -a` (Linux/macOS) или `ver` (Windows)
4. **Error traceback:** Из `logs/errors.log`
5. **Шаги для воспроизведения**
6. **Ожидаемое поведение**
7. **Актуальное поведение**

### Useful Commands

```bash
# System info
python --version
pip list
uname -a

# Django info
python manage.py version
python manage.py check

# Check services
systemctl status shoesbot-django
systemctl status shoesbot-telegram
journalctl -u shoesbot-django -n 50
```

## 🔧 Maintenance

### Regular Tasks

```bash
# Еженедельно: Ротация логов
cd shoessite/logs
gzip errors.log.1
rm errors.log.5

# Ежемесячно: Vacuum database (SQLite)
sqlite3 db.sqlite3 "VACUUM;"

# Ежемесячно: Очистка старых media files
find media/photos -mtime +90 -delete
```

### Backup

```bash
# Backup базы данных
cp shoessite/db.sqlite3 backups/db_$(date +%Y%m%d).sqlite3

# Backup media files
tar -czf backups/media_$(date +%Y%m%d).tar.gz shoessite/media/

# Backup .env
cp .env backups/env_$(date +%Y%m%d)
```

---

**Last Updated**: January 2025

**Still having issues?** Open an issue on GitHub with full error details!
