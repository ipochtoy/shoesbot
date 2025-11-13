# ✅ ПОЛНОСТЬЮ ИСПРАВЛЕНА ИНТЕГРАЦИЯ POCHTOY

## Что было исправлено

### 1. ❌ HTTP 405 ошибка - РЕШЕНО
**Проблема:** URL был неправильный `/api/garage-tg/delete` вместо `/api/garage/delete`

**Решение:** Вернул правильный URL из истории коммитов
```python
# Было (неправильно):
POCHTOY_DELETE_URL = POCHTOY_API_URL.replace('/store', '/delete')
# -> https://pochtoy-test.pochtoy3.ru/api/garage-tg/delete

# Стало (правильно):
POCHTOY_DELETE_URL = 'https://pochtoy-test.pochtoy3.ru/api/garage/delete'
```

**Метод:** POST с JSON body `{'trackings': ['GG123', ...]}`

---

### 2. 🗑️ Кнопка "Удалить все" не удаляла технические сообщения - РЕШЕНО

**Проблема:** Сообщения о результате Pochtoy (✅/❌❌❌) отправлялись через `requests.post` без сохранения `message_id`, поэтому кнопка "Удалить все" не могла их удалить.

**Решение:** Теперь при отправке Pochtoy сообщения:
1. Получаем response от Telegram API
2. Извлекаем `message_id` из ответа
3. Добавляем в `SENT_BATCHES[correlation_id]['message_ids']`
4. Кнопка "Удалить все" удаляет все сообщения включая Pochtoy

**Код:**
```python
resp = requests.post(telegram_url, json={
    'chat_id': chat_id,
    'text': f"📡 Pochtoy:\n{pochtoy_msg}"
}, timeout=5)

# Сохраняем message_id чтобы можно было удалить
if resp.status_code == 200:
    resp_data = resp.json()
    if resp_data.get('ok') and resp_data.get('result'):
        msg_id = resp_data['result'].get('message_id')
        if msg_id:
            # Добавляем в SENT_BATCHES
            from shoesbot.telegram_bot import SENT_BATCHES
            if correlation_id in SENT_BATCHES:
                SENT_BATCHES[correlation_id]['message_ids'].append(msg_id)
```

---

## Измененные файлы

1. **shoessite/photos/pochtoy_integration.py**
   - Исправлен URL: `/api/garage/delete` (не `garage-tg`)
   - Упрощен код - убраны лишние попытки разных методов
   - POST метод с JSON body

2. **shoesbot/django_upload.py**
   - Сохранение `message_id` Pochtoy сообщений
   - Добавление в `SENT_BATCHES` для удаления

---

## Коммиты

1. `7892de5` - fix: correct Pochtoy delete URL - /api/garage/delete not garage-tg
2. `011d504` - fix: save Pochtoy message_id to delete it with 'Delete all' button

---

## Статус

✅ **Код обновлен на сервере**
✅ **Бот перезапущен**
✅ **Django работает**

---

## Как проверить

### 1. Pochtoy delete (405 исправлен)
Удали карточку и в логах должно быть:
```
Deleting from Pochtoy (https://pochtoy-test.pochtoy3.ru/api/garage/delete): ['GG123']
Pochtoy DELETE response: 200
```

### 2. Удаление Pochtoy сообщений
1. Загрузи фото в бота
2. Появится сообщение "📡 Pochtoy: ✅" или "❌❌❌"
3. Нажми "Удалить все"
4. **Все сообщения удалятся** включая Pochtoy

---

## Логи

```bash
ssh gcp-shoesbot
# Django логи
tail -f /home/pochtoy/shoesbot/django.log | grep -i pochtoy

# Бот логи
tail -f /home/pochtoy/shoesbot/bot.log | grep -i pochtoy
```

---

**Готово!** Теперь:
- ✅ Pochtoy delete работает (нет 405)
- ✅ Кнопка "Удалить все" чистит ВСЕ сообщения включая технические

