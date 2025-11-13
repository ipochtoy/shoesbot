# Shoesbot - Quick Reference

> **Для Claude:** Читай этот файл в начале нового чата для контекста проекта.

## 🎯 Что это?
Telegram бот + Django админка для обработки фото товаров с распознаванием штрихкодов и AI-генерацией описаний.

## 🌐 Доступы
- **Админка**: https://pochtoy.us/admin/ (admin/admin123)
- **Сервер**: GCP, доступ через `ssh gcp-shoesbot`
- **Domain**: pochtoy.us (nginx → Django на 8000)

## 📁 Структура проекта
```
/Users/dzianismazol/Projects/shoesbot/     # Локально
/home/pochtoy/shoesbot/                      # На сервере

├── shoessite/                    # Django админка
│   ├── manage.py
│   ├── db.sqlite3               # База данных
│   ├── media/                   # Загруженные фото
│   ├── shoessite/               # Settings
│   │   ├── settings.py          # Prod настройки
│   │   └── settings_dev.py      # Dev настройки
│   └── photos/                  # Основное приложение
│       ├── models.py            # PhotoBatch, Photo, BarcodeResult
│       ├── views.py             # API endpoints
│       ├── fashn_api.py         # FasnAi интеграция
│       └── pochtoy_integration.py  # Pochtoy API
│
├── shoesbot/                     # Telegram бот
│   ├── telegram_bot.py          # Основной бот
│   ├── pipeline.py              # Обработка фото
│   ├── decoders/                # Распознавание кодов
│   └── django_upload.py         # Загрузка в Django
│
├── apps/marketplaces/ebay/       # eBay интеграция
│   ├── models.py                # EbayCandidate, EbayToken
│   └── views.py                 # eBay API
│
└── .env                         # Переменные окружения
```

## 🔧 Ключевые сервисы (systemd)
```bash
# Статус
ssh gcp-shoesbot "systemctl status shoesbot shoesdjango"

# Перезапуск
ssh gcp-shoesbot "sudo systemctl restart shoesbot.service"
ssh gcp-shoesbot "sudo systemctl restart shoesdjango.service"

# Логи
ssh gcp-shoesbot "journalctl -u shoesbot -n 50 --no-pager"
ssh gcp-shoesbot "journalctl -u shoesdjango -n 50 --no-pager"
```

## 🔌 API интеграции

### 1. Pochtoy API (отправка карточек товаров)
```python
# Store (загрузка карточки) - используй PUT
PUT https://pochtoy-test.pochtoy3.ru/api/garage-tg/store
Headers: {'Content-Type': 'application/json', 'Accept': 'application/json'}

# Delete (удаление) - используй POST
POST https://pochtoy-test.pochtoy3.ru/api/garage-tg/delete
```
**Файл**: `shoessite/photos/pochtoy_integration.py`

### 2. FasnAi (генерация фото с моделями)
```python
# Product to Model (👤) - модель в одежде
# Background Change (✨) - улучшение фото
# БУ АА/ББ - добавление логотипов

CLOUDFLARED_URL=https://pochtoy.us  # В .env!
```
**Файл**: `shoessite/photos/fashn_api.py`  
**Логи**: `/tmp/fashn_api.log`, `/tmp/fashn_bg_change.log`

### 3. OpenAI (AI описания)
```python
# Генерация описаний товаров
OPENAI_API_KEY=...  # В .env
```

## 🗄️ База данных
```bash
# Django shell
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py shell"

# Миграции
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py makemigrations"
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py migrate"

# Основные модели
from photos.models import PhotoBatch, Photo, BarcodeResult
from apps.marketplaces.ebay.models import EbayCandidate
```

## 🚀 Деплой
```bash
# Способ 1: Через deploy.sh (безопасно, с откатом)
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot && bash deploy.sh"

# Способ 2: Ручной деплой
cd /Users/dzianismazol/Projects/shoesbot
git add -A && git commit -m "..." && git push origin main
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot && git pull origin main"
ssh gcp-shoesbot "sudo systemctl restart shoesdjango.service"
```

## 🔐 Важные файлы и настройки

### Статика (CSS/JS)
```bash
# Проблема: nginx возвращал 403
# Решение: права 755 на /home/pochtoy/shoesbot/
ssh gcp-shoesbot "chmod 755 /home/pochtoy/shoesbot"

# Collectstatic
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py collectstatic --noinput"
```

### Nginx конфиг
```
/etc/nginx/sites-available/shoesbot
- Проксирует все в Django на :8000
- /static/ раздается через /home/pochtoy/shoesbot/static/
- /media/ раздается через /home/pochtoy/shoesbot/shoessite/media/
```

### WhiteNoise (fallback для статики)
```python
# settings.py
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',  # После SecurityMiddleware
    ...
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

## 🐛 Частые проблемы и решения

### 1. Статика не загружается (403)
```bash
# Проверь права
ssh gcp-shoesbot "chmod 755 /home/pochtoy/shoesbot"
ssh gcp-shoesbot "bash /home/pochtoy/shoesbot/fix_static_permissions.sh"
```

### 2. FasnAi не работает (HTTP 500)
```bash
# Проверь CLOUDFLARED_URL в .env
ssh gcp-shoesbot "grep CLOUDFLARED_URL /home/pochtoy/shoesbot/.env"
# Должно быть: CLOUDFLARED_URL=https://pochtoy.us

# Проверь логи
ssh gcp-shoesbot "tail -50 /tmp/fashn_api.log"
```

### 3. Pochtoy API возвращает 405
```bash
# Store: используй PUT (не POST!)
# Delete: используй POST
# Endpoint: /api/garage-tg/ (не /api/garage/)
```

### 4. Миграции не применены
```bash
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py migrate"
```

## 📝 Полезные команды

### Проверка системы
```bash
# Все в одном
ssh gcp-shoesbot "systemctl is-active shoesbot shoesdjango && curl -s http://localhost:8000/admin/ | head -1"

# Статика
curl -I https://pochtoy.us/static/admin/css/base.css

# Проверка .env
ssh gcp-shoesbot "grep -E 'FASHN|OPENAI|POCHTOY|CLOUDFLARED' /home/pochtoy/shoesbot/.env | sed 's/=.*/=***/')"
```

### Очистка
```bash
# Удалить старые фото (оставить N последних)
ssh gcp-shoesbot "cd /home/pochtoy/shoesbot/shoessite && ../.venv/bin/python manage.py shell"
>>> from photos.models import Photo
>>> Photo.objects.order_by('-uploaded_at')[100:].delete()
```

## 📚 Документация
- `CLAUDE_CODE_INSTRUCTIONS.md` - Инструкции для Claude
- `СТАТИКА_ИСПРАВЛЕНА.md` - Решение проблемы со статикой
- `FASHN_AI_FIXED.md` - Исправление FasnAi API
- `ФИНАЛЬНЫЙ_ОТЧЕТ_ИСПРАВЛЕНИЙ.md` - Полный отчет о фиксах
- `deploy.sh` - Скрипт безопасного деплоя

## 🎨 Функции в админке

### Карточка товара (`/photos/card/<id>/`)
- 📸 Управление фото (rotate, delete, set main)
- 👤 Ghost Mannequin (FasnAi - модель в одежде)
- ✨ Product Beautifier (FasnAi - улучшение фото)
- АА/ББ Логотипы для БУ товаров
- 🤖 AI генерация описания (OpenAI)
- 🔍 Поиск по баркоду

### eBay интеграция (`/admin/ebay/`)
- Подготовка листингов
- Публикация на eBay
- Управление ценами
- AI анализ товаров

## 🔄 Workflow разработки
1. Локально: редактируй код
2. Коммит: `git add -A && git commit -m "..." && git push`
3. Деплой: `ssh gcp-shoesbot "cd /home/pochtoy/shoesbot && bash deploy.sh"`
4. Проверка: открой https://pochtoy.us/admin/

## 🚨 Священные правила
1. **НЕ трогай бота** без крайней нужды (работает стабильно)
2. **Всегда делай бекап** перед изменениями в базе
3. **Используй deploy.sh** для продакшена (авто-откат при ошибках)
4. **Проверяй права** после collectstatic: `chmod 755 /home/pochtoy/shoesbot`
5. **Поchtoy API**: store=PUT, delete=POST, endpoint=/api/garage-tg/

## 💡 Начало работы в новом чате
Просто скажи Claude:
> "Читай QUICK_START.md и CLAUDE_CODE_INSTRUCTIONS.md, потом [твоя задача]"

---
**Последнее обновление**: 2025-11-13  
**Версия**: 1.0

