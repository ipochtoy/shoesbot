# ShoesBot - Система управления товарами с фото

Система для автоматической обработки фотографий товаров, извлечения баркодов, QR-кодов и создания карточек товаров с AI-анализом.

## 📖 Документация

**→ [Полная документация](docs/README.md)** - Начните здесь!

- [Архитектура](docs/ARCHITECTURE.md) - Подробное описание архитектуры с Mermaid диаграммами
- [Установка и Настройка](docs/SETUP.md) - Пошаговая инструкция по установке
- [API Документация](docs/API.md) - Описание всех 33 API endpoints
- [Решение Проблем](docs/TROUBLESHOOTING.md) - Частые проблемы и их решения

## ⭐ Что Нового в v2.0 (Январь 2025)

✅ **Полный рефакторинг кодовой базы:**
- Service layer для всех внешних API (OpenAI, FASHN, eBay)
- Modular views (2758 → 10 модулей по ~200 строк)
- Custom middleware (logging, performance, error handling)
- Frontend модули (Alpine.js + Axios)
- Bot refactoring (config, helpers, MessageSender)
- Comprehensive documentation с Mermaid диаграммами

**Результат:** -1,354 строк дублирования, +2,867 строк чистого кода, 100% type hints

## 🎯 Основные возможности

### Telegram Бот
- Автоматическое извлечение баркодов и QR-кодов из фотографий
- Поддержка нескольких декодеров (zbar, opencv-qr, Google Vision OCR)
- Метрики производительности каждого декодера
- Отправка карточек товаров с результатами сканирования

### Django Веб-интерфейс
- 📸 **Управление фото товаров:**
  - Загрузка фото с компьютера
  - Поиск стоковых фото (Google Images, eBay, Bing)
  - Поворот фото (влево/вправо)
  - Установка главного фото для превью
  - Удаление фото

- 🤖 **AI-анализ товаров:**
  - Генерация сводки по товару (OpenAI GPT-4o Vision)
  - Анализ фото, баркодов и GG-лейб
  - Автоматическое заполнение карточки товара
  - Поиск цен на eBay
  - Голосовой ввод для редактирования

- 📊 **Обработка баркодов:**
  - Поиск информации по баркоду
  - Google Lens интеграция
  - Отображение найденных данных

## 📋 Структура проекта

```
shoesbot/
├── shoesbot/              # Telegram бот (модульная структура)
│   ├── telegram_bot.py    # Основной файл бота
│   ├── config.py          # Конфигурация (все константы)
│   ├── helpers.py         # Переиспользуемые функции
│   ├── message_sender.py  # Централизованная отправка сообщений
│   ├── pipeline.py        # Pipeline обработки декодеров
│   ├── models.py          # Модели данных
│   └── decoders/          # Декодеры баркодов (ZBar, OpenCV, GG Label, OpenAI)
│
├── shoessite/             # Django веб-приложение
│   ├── manage.py
│   ├── logs/              # Rotating logs (requests, errors, performance)
│   ├── shoessite/         # Настройки Django
│   │   └── settings.py    # Middleware, Logging конфигурация
│   └── photos/            # Приложение для работы с фото
│       ├── models.py      # Модели БД (PhotoBatch, Photo, BarcodeResult)
│       ├── views/         # **Модульная структура** (10 файлов)
│       │   ├── __init__.py    # Re-exports (backward compatibility)
│       │   ├── upload.py      # Upload endpoints (315 lines)
│       │   ├── photos.py      # Photo management (189 lines)
│       │   ├── ai.py          # AI generation (176 lines)
│       │   ├── search.py      # eBay search (775 lines)
│       │   ├── barcodes.py    # Barcode operations (449 lines)
│       │   ├── enhance.py     # FASHN enhancement (206 lines)
│       │   └── ...            # admin, buffer, webhook
│       ├── services/      # **Service layer**
│       │   ├── api_client.py   # Base API client (retry, timeout, logging)
│       │   ├── ai_service.py   # OpenAI integration (678 lines)
│       │   ├── fashn_service.py # FASHN AI integration (276 lines)
│       │   ├── search_service.py # eBay integration (235 lines)
│       │   └── image_service.py # Image processing (328 lines)
│       ├── middleware/    # **Custom middleware**
│       │   ├── request_logging.py    # Log all requests
│       │   ├── error_handling.py     # Catch exceptions, return JSON
│       │   └── performance.py        # Track slow requests (>2s, >5s)
│       ├── utils/
│       │   └── error_handlers.py # API response utilities
│       ├── static/photos/js/  # **Frontend modules**
│       │   ├── api.js         # Axios API calls (277 lines)
│       │   ├── ui.js          # UI utilities, toasts (389 lines)
│       │   └── photo-card.js  # Card logic (660 lines)
│       └── templates/     # HTML шаблоны
│
├── docs/                  # **Comprehensive documentation**
│   ├── README.md          # Main docs with Mermaid diagrams
│   ├── ARCHITECTURE.md    # Architecture details
│   ├── SETUP.md           # Installation guide
│   ├── API.md             # 33 endpoints documented
│   └── TROUBLESHOOTING.md # Common issues
│
├── .venv/                 # Python виртуальное окружение
├── .env                   # Переменные окружения (не в git)
├── requirements.txt       # Зависимости
└── README.md             # Этот файл
```

**См. [ARCHITECTURE.md](docs/ARCHITECTURE.md) для диаграмм и деталей.**

## 🚀 Быстрый Старт

**→ См. [SETUP.md](docs/SETUP.md) для подробной инструкции**

## 🚀 Установка (Кратко)

### 1. Системные зависимости (macOS)

```bash
# Установка zbar для декодирования баркодов
brew install zbar
```

### 2. Python окружение

```bash
# Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate  # или на Windows: .venv\Scripts\activate

# Установка зависимостей для бота
pip install -r requirements.txt

# Установка зависимостей для Django (если отдельный файл)
cd shoessite
pip install django pillow requests beautifulsoup4 openai python-dotenv
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BACKEND_URL=http://localhost:8000

# OpenAI (обязательно)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o

# FASHN AI (обязательно)
FASHN_API_KEY=your_fashn_api_key_here

# eBay API (опционально)
EBAY_APP_ID=your_ebay_app_id

# Google Cloud Vision (опционально)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Django
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=*
```

### 4. Настройка базы данных Django

```bash
cd shoessite
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # Создание админ-пользователя
```

## 🏃 Запуск

### Запуск Telegram бота

```bash
# macOS: DYLD_LIBRARY_PATH нужен для pyzbar
DYLD_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python shoesbot/telegram_bot.py

# Или в фоне:
DYLD_LIBRARY_PATH=/opt/homebrew/lib nohup .venv/bin/python shoesbot/telegram_bot.py > bot.log 2>&1 &
```

### Запуск Django веб-сервера

```bash
cd shoessite
python manage.py runserver 0.0.0.0:8000
```

Веб-интерфейс будет доступен по адресу: `http://localhost:8000`

## 📱 Использование

### Telegram бот

1. Отправьте фото товара боту
2. Бот автоматически извлечет баркоды и QR-коды
3. Отправит карточку товара с результатами

**Команды бота:**
- `/start` - старт
- `/ping` - проверка работы
- `/debug_on` - подробные логи
- `/debug_off` - обычные логи
- `/diag` - информация о системе
- `/stats` - статистика по последним фото

### Веб-интерфейс

1. Откройте `http://localhost:8000/admin` и войдите как суперпользователь
2. Перейдите в раздел "Карточки товаров" (Photo Batches)
3. Откройте карточку товара для редактирования

**Основные функции:**

- **📸 Управление фото:**
  - ➕ Добавить фото с компьютера
  - 🔍 Найти стоковые фото (поиск в Google, eBay, Bing)
  - ⭐ Сделать фото главным (для превью)
  - ↶ ↷ Повернуть фото
  - ✕ Удалить фото

- **🤖 AI-анализ:**
  - ✨ Сгенерировать сводку (анализ фото + баркодов + AI)
  - ✏️ Редактировать сводку (текст или голосом)
  - ✅ Применить сводку к карточке (автозаполнение полей)

- **📊 Поиск информации:**
  - Поиск по баркоду (Google Lens, Google Shopping, Bing)
  - Отображение найденных цен и изображений

## 🔧 API Endpoints

**→ См. [API.md](docs/API.md) для полной документации 33 endpoints**

### Основные категории:

1. **Upload & Buffer** (10 endpoints) - Загрузка и буферизация фото
2. **Photo Management** (6 endpoints) - Управление фото (rotate, delete, reorder)
3. **AI & Enhancement** (4 endpoints) - OpenAI summary, FASHN enhancement
4. **Search & Barcodes** (4 endpoints) - Поиск по баркодам, eBay integration
5. **Admin & Webhooks** (4 endpoints) - Админ задачи, Pochtoy webhook

## 🗄️ Модели данных

### PhotoBatch (Карточка товара)
- `correlation_id` - уникальный ID карточки
- `title`, `description`, `price`, `brand`, `size`, `color`, `category`, `condition`
- `status` - статус обработки (pending, processed, failed)

### Photo (Фото)
- `batch` - связь с карточкой товара
- `image` - файл изображения
- `is_main` - главное фото (для превью)
- `order` - порядок отображения

### BarcodeResult (Баркод)
- `photo` - связь с фото
- `symbology` - тип баркода (UPCA, QRCODE, CODE39 и т.д.)
- `data` - данные баркода
- `source` - источник обнаружения (zbar, opencv-qr, vision-ocr, gg-label)

## 🔐 Безопасность

- Файл `.env` не должен попадать в git (добавлен в `.gitignore`)
- Используйте сильный `SECRET_KEY` для Django
- Ограничьте `ALLOWED_HOSTS` в production
- Не храните API ключи в коде

## 🐛 Решение проблем

**→ См. [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) для подробного руководства**

### Быстрые решения:

```bash
# Django не запускается
python manage.py migrate
python manage.py runserver

# Bot не отвечает
pkill -f telegram_bot.py
python telegram_bot.py

# Проверка логов
tail -f shoessite/logs/errors.log
tail -f shoessite/logs/performance.log
```

## 📈 Метрики Рефакторинга

**До:**
- views.py: 2758 строк
- Дублирование кода: ~1000+ строк
- AI интеграции: разбросаны по коду
- Error handling: повторяющиеся try-except блоки

**После:**
- views/: 10 модулей по ~200 строк
- Services layer: переиспользуемые компоненты
- Middleware: централизованная обработка
- Error handling utilities + декоратор

**Результат:**
- ✅ -1,354 строк дублирования
- ✅ +2,867 строк чистого кода
- ✅ 100% type hints в сервисах
- ✅ Comprehensive documentation

## 🔄 Откат к Предыдущей Версии

Если что-то пошло не так:

```bash
# Вернуться к версии до рефакторинга
git checkout backup/pre-refactoring-2025-01-10

# Или использовать tag
git checkout backup-before-refactoring
```

## 📄 Лицензия

Проект для внутреннего использования.

## 👤 Автор

Разработано для управления товарами с автоматическим анализом фото и баркодов.

## 🛠️ Технологии

- **Backend**: Python 3.9+, Django 4.2, python-telegram-bot
- **AI**: OpenAI GPT-4 Vision, FASHN AI (Product to Model)
- **Search**: eBay Finding API, Google Cloud Vision (optional)
- **Barcode**: pyzbar (ZBar), OpenCV, Custom GG Label decoder
- **Frontend**: Alpine.js 3.x, Axios, Vanilla JS modules
- **Infrastructure**: Custom middleware, rotating logs, error handling utilities

## 📚 Further Reading

- [Architecture Details](docs/ARCHITECTURE.md) - Mermaid diagrams, design decisions
- [Setup Guide](docs/SETUP.md) - Installation, deployment, configuration
- [API Documentation](docs/API.md) - All 33 endpoints with examples
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Solutions to common issues

---

**Version**: 2.0 (Post-Refactoring)
**Last Updated**: Январь 2025
**License**: Internal use only
