# Фикс: товары не заливаются в Django на VM

## Проблема
После деплоя на VM бот не может загрузить товары в Django.

## Причины и решения

### 1. Проверь что Django запущен на VM

```bash
# Подключись к VM
ssh gcp-shoesbot

# Проверь статус Django
sudo systemctl status shoesdjango.service

# Если не запущен:
sudo systemctl start shoesdjango.service
sudo systemctl restart shoesdjango.service
```

### 2. Проверь URL в .env на VM

Бот использует `DJANGO_API_URL` для связи с Django.

```bash
# На VM проверь .env
cat ~/shoesbot/.env | grep DJANGO

# Должно быть:
DJANGO_API_URL=http://127.0.0.1:8000/photos/api/upload-batch/
```

Если этой строки нет или она неправильная, добавь в `.env` на VM:

```bash
nano ~/shoesbot/.env

# Добавь строку:
DJANGO_API_URL=http://127.0.0.1:8000/photos/api/upload-batch/

# Сохрани: Ctrl+O, Enter, Ctrl+X
```

### 3. Проверь порт Django

```bash
# На VM проверь на каком порту слушает Django
sudo netstat -tlnp | grep 8000
# или
sudo lsof -i :8000

# Должен быть процесс gunicorn на порту 8000
```

### 4. Проверь логи бота

```bash
# На VM смотри логи бота
tail -f ~/shoesbot/bot.log

# Ищи строки с "django_upload" при отправке фото
# Должны быть:
# - "django_upload: uploaded batch XXXX: ..."  (успех)
# или
# - "django_upload: failed 500: ..." (ошибка)
```

### 5. Проверь логи Django

```bash
# На VM смотри логи Django
tail -f ~/shoesbot/django.log

# При отправке фото должны быть запросы к /photos/api/upload-batch/
```

### 6. Перезапусти оба сервиса

```bash
# На VM
sudo systemctl restart shoesbot.service
sudo systemctl restart shoesdjango.service

# Проверь статус
sudo systemctl status shoesbot.service
sudo systemctl status shoesdjango.service
```

---

## Быстрая диагностика

Запусти этот скрипт на VM:

```bash
#!/bin/bash
echo "=== Django Service Status ==="
sudo systemctl status shoesdjango.service | head -10

echo -e "\n=== Django Port ==="
sudo lsof -i :8000

echo -e "\n=== DJANGO_API_URL в .env ==="
grep DJANGO ~/shoesbot/.env

echo -e "\n=== Последние ошибки в bot.log ==="
tail -50 ~/shoesbot/bot.log | grep -i django

echo -e "\n=== Последние ошибки в django.log ==="
tail -50 ~/shoesbot/django.log | grep -i error
```

Сохрани как `~/diagnose_django.sh`, сделай исполняемым и запусти:

```bash
chmod +x ~/diagnose_django.sh
./diagnose_django.sh
```

---

## Если ничего не помогло

### Проверь доступность Django изнутри бота

```bash
# На VM
curl http://127.0.0.1:8000/admin/
# Должен вернуть HTML страницу логина Django

# Проверь API endpoint
curl -X POST http://127.0.0.1:8000/photos/api/upload-batch/ \
  -H "Content-Type: application/json" \
  -d '{"test": "test"}'
# Должен вернуть ошибку но НЕ "Connection refused"
```

### Проверь firewall

```bash
# На VM
sudo ufw status
# Если активен, проверь что порт 8000 открыт для localhost
```

---

## Самая частая причина

**Django не запущен или упал.**

Решение:
```bash
sudo systemctl restart shoesdjango.service
sudo systemctl status shoesdjango.service
```

---

## Пришли мне вывод команд

Если не работает, запусти на VM и пришли результат:

```bash
# 1. Статус сервисов
sudo systemctl status shoesbot.service --no-pager
sudo systemctl status shoesdjango.service --no-pager

# 2. Что в .env
grep DJANGO ~/shoesbot/.env

# 3. Последние 30 строк логов
tail -30 ~/shoesbot/bot.log
tail -30 ~/shoesbot/django.log

# 4. Порт Django
sudo lsof -i :8000
```

