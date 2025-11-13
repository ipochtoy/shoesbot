# Тестовая среда для разработки

## Проблема
При разработке изменений Django может перезапускаться, что мешает работе бота.

## Решение: Отдельный порт для разработки

### Вариант 1: Локальная разработка (рекомендуется)

1. **Разрабатывай локально:**
```bash
cd shoessite
python manage.py runserver 0.0.0.0:8001
```

2. **Тестируй на `http://localhost:8001`**

3. **Когда готово - деплой на сервер:**
```bash
# Копируешь только измененные файлы
scp apps/marketplaces/ebay/views.py gcp-shoesbot:~/shoesbot/apps/marketplaces/ebay/views.py
scp apps/marketplaces/ebay/templates/ebay/candidate_analyze.html gcp-shoesbot:~/shoesbot/apps/marketplaces/ebay/templates/ebay/candidate_analyze.html

# Django на сервере автоматически перезагрузится (если использует --reload)
```

### Вариант 2: Отдельный Django на сервере (порт 8001)

1. **Запусти DEV Django на порту 8001:**
```bash
ssh gcp-shoesbot
cd ~/shoesbot/shoessite
source ../.venv/bin/activate
python manage.py runserver 0.0.0.0:8001
```

2. **Тестируй на `https://pochtoy.us:8001` или через SSH туннель:**
```bash
ssh -L 8001:localhost:8001 gcp-shoesbot
# Открой http://localhost:8001
```

3. **Production Django (порт 8000) продолжает работать для бота**

### Вариант 3: Feature Flags (для безопасного деплоя)

Добавить проверку `ENVIRONMENT` в коде:
```python
# В settings.py
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

# В views.py
if settings.ENVIRONMENT == 'development':
    # Новая логика
else:
    # Старая логика
```

## Рекомендация

**Используй Вариант 1 (локальная разработка):**
- Разрабатывай локально на порту 8001
- Тестируй локально
- Когда готово - деплой на сервер
- Production бот не затронут

## Текущая ситуация

- **Production Django:** порт 8000 (бот использует `http://127.0.0.1:8000`)
- **DEV Django:** можно запустить на порту 8001 для тестирования

