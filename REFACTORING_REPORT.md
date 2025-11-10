# Отчет о разбиении views.py на модули

## Выполнено: 2025-11-10

### Исходная структура
- **Файл**: `shoessite/photos/views.py`
- **Размер**: 2758 строк, 115 KB
- **Проблема**: Монолитный файл, сложно поддерживать

### Новая структура
```
photos/views/
├── __init__.py       # 145 строк - Re-export всех функций
├── upload.py         # 315 строк - Загрузка фото
├── photos.py         # 189 строк - Управление фото
├── ai.py             # 176 строк - AI операции
├── search.py         # 775 строк - Поиск и баркоды
├── barcodes.py       # 449 строк - Обработка баркодов
├── admin.py          # 201 строк - Админские функции
├── buffer.py         # 376 строк - Буфер сортировки
├── webhook.py        # 35 строк  - Вебхуки
└── enhance.py        # 206 строк - FASHN AI улучшение
```

**Итого**: 2867 строк в 10 файлах (увеличение из-за imports и docstrings)

### Распределение функций

#### upload.py (4 функции)
- `upload_batch()` - основная загрузка из Telegram
- `upload_photo_from_computer()` - загрузка с ПК
- `add_photo_from_url()` - добавление по URL
- `buffer_upload()` - загрузка в буфер

#### photos.py (4 функции)
- `set_main_photo()` - установить главное фото
- `move_photo()` - переместить фото вверх/вниз
- `delete_photo()` - удалить фото
- `rotate_photo()` - повернуть фото

#### ai.py (3 функции)
- `generate_summary_api()` - генерация описания товара
- `generate_from_instruction_api()` - генерация по голосовой инструкции
- `save_ai_summary()` - сохранить AI сводку

#### search.py (9 функций)
- `search_by_barcode()` - поиск по баркоду
- `search_stock_photos_api()` - API поиска стоковых фото
- `search_google_images()` - поиск через Google Custom Search
- `search_google_images_web()` - веб-поиск изображений
- `search_with_google_lens()` - поиск через Google Lens
- `search_product_with_vision_api()` - поиск через Vision API
- `search_bing_images()` - поиск через Bing
- `search_product_info()` - поиск информации о товаре
- `search_stock_photos()` - helper для поиска стоковых фото

#### barcodes.py (4 функции)
- `reprocess_photo()` - повторная обработка фото
- `add_barcode_manually()` - добавить баркод вручную
- `process_with_google_vision_direct()` - helper для Google Vision
- `process_with_openai_vision()` - helper для OpenAI Vision

#### admin.py (4 функции)
- `product_card_detail()` - страница карточки товара
- `process_task()` - обработка задач
- `process_google_vision()` - helper для Google Vision
- `process_azure_cv()` - helper для Azure CV

#### buffer.py (9 функций)
- `sorting_view()` - страница сортировки
- `update_photo_group()` - обновить группу фото
- `send_group_to_bot()` - создать карточку из группы
- `detect_gg_in_buffer()` - распознать GG лейблы
- `send_group_to_pochtoy()` - отправить в Pochtoy
- `clear_buffer()` - очистить буфер
- `delete_card_by_correlation()` - удалить карточку
- `get_last_card()` - получить последнюю карточку
- `delete_buffer_photo()` - удалить фото из буфера

#### webhook.py (1 функция)
- `pochtoy_webhook()` - webhook от Pochtoy

#### enhance.py (1 функция)
- `enhance_photo()` - улучшение фото через FASHN AI

### Преимущества новой структуры

1. **Читаемость**: каждый файл отвечает за одну область функциональности
2. **Поддерживаемость**: легко найти нужную функцию
3. **Тестируемость**: можно тестировать каждый модуль отдельно
4. **Обратная совместимость**: все импорты работают через `photos.views.*`

### Проверка

✅ Синтаксис всех файлов проверен (`py_compile`)
✅ Старый файл сохранен как `views.py.backup`
✅ Все 39 функций экспортированы через `__init__.py`
✅ Структура готова к использованию

### Следующие шаги

1. Запустить Django и проверить работоспособность
2. Запустить тесты (если есть)
3. При успехе удалить `views.py.backup`
4. Создать коммит

### Команда для отката (если нужно)

```bash
cd /home/user/shoesbot/shoessite/photos
rm -rf views/
mv views.py.backup views.py
```

---
**Автор**: Claude (Anthropic)
**Дата**: 2025-11-10
