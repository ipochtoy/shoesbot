# Настройка домена pochtoy.us

## Шаг 1: Настрой DNS (СЕЙЧАС)

Зайди в панель управления доменом `pochtoy.us` и добавь A-запись:

```
Тип: A
Имя: @
Значение: 34.45.43.105
TTL: 300 (или Auto)
```

Или если это поддомен:
```
Тип: A  
Имя: www
Значение: 34.45.43.105
TTL: 300
```

**Сделай это прямо сейчас, пока настраиваю остальное!**

---

## Шаг 2: Запусти команды на VM

```bash
# Подключись к VM
ssh gcp-shoesbot

# Установи nginx и certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Создай конфиг nginx
sudo nano /etc/nginx/sites-available/shoesbot
```

Вставь этот конфиг:

```nginx
server {
    listen 80;
    server_name pochtoy.us www.pochtoy.us;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/pochtoy/shoesbot/shoessite/static/;
    }

    location /media/ {
        alias /home/pochtoy/shoesbot/shoessite/media/;
    }
}
```

Сохрани: `Ctrl+O`, `Enter`, `Ctrl+X`

```bash
# Включи конфиг
sudo ln -sf /etc/nginx/sites-available/shoesbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Проверь конфиг
sudo nginx -t

# Перезапусти nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## Шаг 3: Обнови Django settings

```bash
# На VM
nano ~/shoesbot/shoessite/shoessite/settings.py
```

Найди строку `ALLOWED_HOSTS` и измени на:

```python
ALLOWED_HOSTS = ['pochtoy.us', 'www.pochtoy.us', '34.45.43.105', 'localhost', '127.0.0.1']
```

Сохрани и перезапусти Django:

```bash
sudo systemctl restart shoesdjango.service
```

## Шаг 4: Проверь DNS (через 5-10 минут)

```bash
# На своем компьютере
ping pochtoy.us
# Должен показать: 34.45.43.105
```

Или открой в браузере: **http://pochtoy.us/admin/**

Если DNS еще не обновился, подожди еще 5 минут.

## Шаг 5: Настрой HTTPS

Когда домен заработал (шаг 4), на VM запусти:

```bash
sudo certbot --nginx -d pochtoy.us -d www.pochtoy.us
```

Ответь на вопросы:
- Email: твой email для уведомлений
- Agree to terms: `Y`
- Share email: `N` (можно)
- Redirect HTTP to HTTPS: `2` (Yes)

## Шаг 6: Готово! 🎉

Админка теперь доступна:

👉 **https://pochtoy.us/admin/**

---

## Траблшутинг

### DNS не обновился
```bash
# Проверь
nslookup pochtoy.us
# Должен показать 34.45.43.105
```

Если нет - подожди еще, DNS может обновляться до 24 часов (но обычно 5-10 минут).

### Nginx не запускается
```bash
# Проверь ошибки
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Certbot ошибка
Убедись что:
- DNS обновился (ping pochtoy.us показывает 34.45.43.105)
- Nginx запущен (sudo systemctl status nginx)
- Порты 80 и 443 открыты в firewall

### Открыть порты в Google Cloud
Если нужно:
```bash
# Через веб-консоль
https://console.cloud.google.com/networking/firewalls/list

# Создай правила для:
# - tcp:80 (HTTP)
# - tcp:443 (HTTPS)
```

