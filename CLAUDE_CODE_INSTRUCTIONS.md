# Инструкция для Claude Code: Настройка Dev Django окружения

## Задача
Настроить доступ к dev Django через `https://pochtoy.us/dev/admin/` без влияния на production и бота.

## Текущая ситуация

### Что работает:
- ✅ Production Django: `https://pochtoy.us/admin/` (порт 8000)
- ✅ Bot: работает через systemd service
- ✅ Dev Django: запущен на порту 8001 с отдельной БД (`dev_db.sqlite3`)

### Что не работает:
- ❌ `https://pochtoy.us/dev/admin/` возвращает 404
- ❌ Nginx конфиг не применен (нужен sudo пароль для копирования файла)

## Структура проекта

### Сервер
- **SSH:** `ssh gcp-shoesbot`
- **Путь проекта:** `/home/pochtoy/shoesbot/`
- **Nginx конфиг:** `/etc/nginx/sites-available/shoesbot`
- **Dev Django:** порт 8001, настройки в `shoessite/shoessite/settings_dev.py`

### Файлы уже готовы:

1. **Nginx конфиг:** `/home/pochtoy/nginx-shoesbot-updated.conf`
   - Добавлен `location /dev/` для проксирования на порт 8001
   - Использует `proxy_pass http://127.0.0.1:8001/;` (trailing slash убирает `/dev/` из пути)

2. **Django dev настройки:** `shoessite/shoessite/settings_dev.py`
   - Отдельная БД: `dev_db.sqlite3`
   - ROOT_URLCONF: `shoessite.urls_dev`

3. **Django dev URLs:** `shoessite/shoessite/urls_dev.py`
   - Обрабатывает пути с префиксом `/dev/`

## Что нужно сделать

### Шаг 1: Применить Nginx конфиг
```bash
# На сервере (потребуется sudo пароль):
sudo cp /home/pochtoy/nginx-shoesbot-updated.conf /etc/nginx/sites-available/shoesbot
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 2: Проверить Dev Django
```bash
# Убедиться что dev Django запущен:
ps aux | grep 'runserver.*8001'

# Если не запущен:
cd ~/shoesbot/shoessite
source ../.venv/bin/activate
python manage.py runserver 0.0.0.0:8001 --settings=shoessite.settings_dev
```

### Шаг 3: Проверить доступность
```bash
# Проверить что nginx правильно проксирует:
curl -k https://pochtoy.us/dev/admin/

# Должен вернуть страницу логина Django admin (HTTP 302 или 200)
```

## Доступы

### SSH доступ
- **Хост:** `gcp-shoesbot` (или IP: `34.45.43.105`)
- **Пользователь:** `pochtoy`
- **SSH ключ:** должен быть настроен в `~/.ssh/config` или использовать стандартный ключ

### Sudo права
Пользователь `pochtoy` имеет права без пароля на:
- `/bin/systemctl * nginx`
- `/bin/systemctl * shoesdjango.service`
- `/bin/systemctl * shoesbot.service`

**НО:** для копирования файлов в `/etc/nginx/` нужен sudo пароль.

### Важные пути
- **Проект:** `/home/pochtoy/shoesbot/`
- **Nginx конфиг:** `/etc/nginx/sites-available/shoesbot`
- **Nginx enabled:** `/etc/nginx/sites-enabled/shoesbot` (симлинк)
- **Готовый конфиг:** `/home/pochtoy/nginx-shoesbot-updated.conf`
- **Dev Django настройки:** `/home/pochtoy/shoesbot/shoessite/shoessite/settings_dev.py`
- **Dev Django URLs:** `/home/pochtoy/shoesbot/shoessite/shoessite/urls_dev.py`

## Текущий Nginx конфиг (production)

```nginx
server {
    server_name pochtoy.us www.pochtoy.us;

    location / {
        proxy_pass http://127.0.0.1:8000;  # Production Django
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/pochtoy/shoesbot/static/;
    }

    location /media/ {
        alias /home/pochtoy/shoesbot/shoessite/media/;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/pochtoy.us/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pochtoy.us/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
```

## Новый Nginx конфиг (нужно применить)

Добавить перед `location /`:

```nginx
    # Dev Django on /dev/ path (must be before location /)
    location /dev/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
```

## Важные моменты

1. **Не трогать production:** порт 8000, production Django, бот
2. **Dev изолирован:** отдельная БД, порт 8001, отдельные настройки
3. **Nginx порядок важен:** `location /dev/` должен быть ПЕРЕД `location /`
4. **Trailing slash в proxy_pass:** `http://127.0.0.1:8001/` (с `/`) автоматически убирает `/dev/` из пути

## Проверка после применения

1. Production должен работать: `https://pochtoy.us/admin/` → редирект на логин
2. Dev должен работать: `https://pochtoy.us/dev/admin/` → редирект на логин
3. Бот должен работать: проверить что нет ошибок в логах

## Если что-то пошло не так

### Откат Nginx конфига:
```bash
sudo cp /etc/nginx/sites-available/shoesbot.backup /etc/nginx/sites-available/shoesbot
sudo nginx -t
sudo systemctl reload nginx
```

### Проверка логов:
```bash
# Nginx ошибки:
sudo tail -f /var/log/nginx/error.log

# Django dev:
tail -f ~/shoesbot/shoessite/django.log

# Bot:
sudo journalctl -u shoesbot.service -f
```

## Альтернативное решение (если sudo не работает)

Если не получается применить nginx конфиг, можно настроить Django dev для работы с префиксом `/dev/` напрямую (через `FORCE_SCRIPT_NAME` или middleware), но это менее правильное решение.

