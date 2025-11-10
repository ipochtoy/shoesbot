# Photos App Middleware

Кастомные middleware для приложения photos.

## Установленные Middleware

### 1. RequestLoggingMiddleware

**Расположение**: `photos.middleware.request_logging.RequestLoggingMiddleware`

**Функции**:
- Логирует все входящие HTTP запросы
- Пропускает статические файлы (/static/, /media/)
- Логирует метод, путь, пользователя, IP адрес
- Для POST запросов к API логирует preview body
- Логирует статус-коды ответов

**Логи**: `logs/requests.log`

**Пример лога**:
```
[INFO] 2025-01-10 10:30:45 photos.requests: Request: {"method": "POST", "path": "/photos/api/upload-batch/", "user": "Anonymous", "ip": "127.0.0.1"}
```

### 2. PerformanceMonitoringMiddleware

**Расположение**: `photos.middleware.performance.PerformanceMonitoringMiddleware`

**Функции**:
- Измеряет время выполнения каждого запроса
- Логирует предупреждение если запрос > 2 секунд
- Логирует ошибку если запрос > 5 секунд
- Добавляет header `X-Request-Duration` в ответ

**Логи**: `logs/performance.log`

**Пример лога**:
```
[WARNING] 2025-01-10 10:31:20 photos.performance: Slow request: POST /photos/api/enhance-photo/123/ took 3.42s
```

### 3. ErrorHandlingMiddleware

**Расположение**: `photos.middleware.error_handling.ErrorHandlingMiddleware`

**Функции**:
- Перехватывает исключения в API endpoints
- Возвращает консистентные JSON ответы
- Обрабатывает разные типы исключений с соответствующими HTTP кодами:
  - `ValidationError` → 400 Bad Request
  - `PermissionDenied` → 403 Forbidden
  - `Http404` → 404 Not Found
  - `ValueError` → 400 Bad Request
  - Остальные → 500 Internal Server Error
- Логирует все исключения с traceback

**Логи**: `logs/errors.log`

**Пример ответа**:
```json
{
    "success": false,
    "error": "Internal server error",
    "details": "Unable to connect to external API"
}
```

## Порядок Middleware

Важен порядок в `settings.py`:

```python
MIDDLEWARE = [
    # ... стандартные Django middleware ...
    'photos.middleware.request_logging.RequestLoggingMiddleware',  # 1. Логирование запроса
    'photos.middleware.performance.PerformanceMonitoringMiddleware',  # 2. Замер времени
    'photos.middleware.error_handling.ErrorHandlingMiddleware',  # 3. Обработка ошибок
]
```

## Error Handling Utilities

Модуль `photos.utils.error_handlers` предоставляет утилиты для консистентных API ответов.

### Функции Success/Error

```python
from photos.utils.error_handlers import api_success, api_error

# Success response
return api_success({'card_id': 123}, message='Card created')
# → {"success": true, "message": "Card created", "card_id": 123}

# Error response
return api_error('Invalid barcode format', details='Expected 13 digits', status=400)
# → {"success": false, "error": "Invalid barcode format", "details": "Expected 13 digits"}
```

### Специализированные функции

```python
from photos.utils.error_handlers import (
    api_validation_error,
    api_not_found,
    error_missing_parameter,
    error_invalid_json,
    error_file_too_large,
    error_unsupported_format,
)

# Validation errors
return api_validation_error('Invalid input', {'email': 'Invalid email format'})

# 404 errors
return api_not_found('Photo')

# Common errors
return error_missing_parameter('photo_id')
return error_file_too_large(10)  # 10MB
return error_unsupported_format(['jpg', 'png'])
```

### Декоратор для автоматической обработки

```python
from photos.utils.error_handlers import handle_exceptions

@handle_exceptions
def my_view(request):
    # Ваш код - исключения будут автоматически обработаны
    value = int(request.GET['value'])  # Может вызвать ValueError
    return api_success({'result': value * 2})
```

## Конфигурация Логирования

Настроено в `settings.py`:

- **Console**: Все логи выводятся в консоль (для разработки)
- **File**: Логи записываются в файлы с ротацией (10MB, 5 backups)
- **Уровни**:
  - `DEBUG` режим: DEBUG level для photos.*
  - `Production`: INFO level для photos.*

### Логи по категориям

- `photos.requests` → `logs/requests.log` (все запросы)
- `photos.errors` → `logs/errors.log` (ошибки)
- `photos.performance` → `logs/performance.log` (медленные запросы)
- `photos.services` → console (работа сервисов)

## Примеры Использования

### Использование в Views

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from photos.utils.error_handlers import api_success, api_error, handle_exceptions
import logging

logger = logging.getLogger('photos.views')

@handle_exceptions
@require_http_methods(["POST"])
def my_api_endpoint(request):
    # Исключения автоматически обрабатываются декоратором
    data = json.loads(request.body)

    if 'required_field' not in data:
        return api_error('Missing required field', status=400)

    # Ваша логика
    logger.info(f"Processing data: {data}")
    result = process_data(data)

    return api_success({'result': result}, message='Success')
```

### Мониторинг Performance

Если запрос медленный, middleware автоматически залогирует:

```
[WARNING] photos.performance: Slow request: POST /photos/api/enhance-photo/456/ took 3.15s
```

Вы можете проверить header в ответе:
```python
# Response headers
X-Request-Duration: 3.150s
```

### Отладка Ошибок

Все ошибки в API endpoints автоматически логируются в `logs/errors.log` с полным traceback:

```
[ERROR] 2025-01-10 10:35:12 photos.errors: Exception in POST /photos/api/some-endpoint/: Division by zero
Traceback (most recent call last):
  File "...", line XX, in process_exception
    ...
ZeroDivisionError: division by zero
```

## Best Practices

1. **Используйте error_handlers утилиты** вместо прямых JsonResponse
2. **Добавляйте логирование** в критических местах вашего кода
3. **Используйте декоратор @handle_exceptions** для упрощения error handling
4. **Мониторьте performance.log** для оптимизации медленных endpoints
5. **Проверяйте errors.log** регулярно для выявления проблем
