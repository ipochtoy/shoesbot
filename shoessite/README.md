# Shoes Bot Django Admin

Админка для обработки фото из Telegram бота.

## Доступ

- **URL**: http://127.0.0.1:8000/admin/
- **Логин**: admin
- **Пароль**: admin

## Модели

- **PhotoBatch** - батчи фото из бота
- **Photo** - отдельные фото
- **BarcodeResult** - найденные баркоды
- **ProcessingTask** - задачи для дополнительной обработки с разными API

## API Endpoint

Бот автоматически загружает фото через:
- `POST /photos/api/upload-batch/`

## Дополнительная обработка

В админке можно создавать ProcessingTask для обработки фото разными API:
- Google Vision (дополнительные проверки)
- Azure Computer Vision
- AWS Rekognition
- и т.д.

