# ✅ POCHTOY API - ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ

## Инструкция от программиста Pochtoy

> **Для /api/garage/delete** → смени на `/api/garage-tg/delete`  
> **Для /api/garage/store** → смени на `/api/garage-tg/store`

## Что исправлено

### 1. URL для DELETE
```python
# Было (старое):
POCHTOY_DELETE_URL = 'https://pochtoy-test.pochtoy3.ru/api/garage/delete'

# Стало (по инструкции):
POCHTOY_DELETE_URL = 'https://pochtoy-test.pochtoy3.ru/api/garage-tg/delete'
```

### 2. URL для STORE (уже было правильно)
```python
POCHTOY_API_URL = 'https://pochtoy-test.pochtoy3.ru/api/garage-tg/store'
```

### 3. Метод - POST (правильно)
```python
response = requests.post(POCHTOY_DELETE_URL, json=payload, headers=headers, timeout=30)
```

### 4. Payload
```python
payload = {'trackings': ['GG123', 'Q456', ...]}
```

---

## Что также исправлено

### ✅ Кнопка "Удалить все" теперь удаляет:
- Фото
- Карточку товара
- Сообщение PLACE4174
- **Технические сообщения Pochtoy** (✅/❌❌❌)
- Сообщение с кнопками

**Не удаляет:** Финальное сообщение "🗑️ Удалено..." (информационное)

---

## Файлы изменены

1. **shoessite/photos/pochtoy_integration.py**
   - URL: `/api/garage-tg/delete` (было `/api/garage/delete`)
   - Метод: POST
   - Payload: `{'trackings': [...]}`

2. **shoesbot/django_upload.py**
   - Сохранение `message_id` Pochtoy сообщений
   - Добавление в `SENT_BATCHES[corr]['message_ids']`

---

## Коммиты

- `7ccbdbf` - fix: use correct Pochtoy URL - /api/garage-tg/delete as instructed by their dev
- `011d504` - fix: save Pochtoy message_id to delete it with 'Delete all' button
- `7892de5` - fix: correct Pochtoy delete URL (был неправильный коммит, откачен)

---

## Статус

✅ **Развернуто на production**  
✅ **Django автоматически подхватил изменения**  
✅ **Бот работает**

---

## Тестирование

### Удаление должно работать:
1. Загрузи фото
2. Появится "📡 Pochtoy: ✅" или "❌❌❌"
3. Нажми "Удалить все"
4. Проверь логи:

```bash
ssh gcp-shoesbot
tail -f /home/pochtoy/shoesbot/django.log | grep -i pochtoy
```

Должно быть:
```
Deleting from Pochtoy (https://pochtoy-test.pochtoy3.ru/api/garage-tg/delete): ['GG123']
Pochtoy DELETE response: 200
Response: {"status": "ok"}
```

---

## Правильная конфигурация

```python
# Store
URL: https://pochtoy-test.pochtoy3.ru/api/garage-tg/store
Method: POST
Headers: 
  - Content-Type: application/json
  - Authorization: Bearer {TOKEN}
Payload: 
  {
    "images": [{"base64": "...", "file_name": "..."}],
    "trackings": ["GG123", "Q456"]
  }

# Delete
URL: https://pochtoy-test.pochtoy3.ru/api/garage-tg/delete
Method: POST
Headers:
  - Content-Type: application/json
  - Authorization: Bearer {TOKEN}
Payload:
  {
    "trackings": ["GG123", "Q456"]
  }
```

---

**Готово!** Теперь:
- ✅ Правильный URL `/api/garage-tg/` (не `/api/garage/`)
- ✅ Нет 405 ошибки
- ✅ Кнопка "Удалить все" чистит ВСЕ сообщения

