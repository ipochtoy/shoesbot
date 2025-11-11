# Настройка домена для Django админки

## Быстрый старт

### 1. Выбери домен
Например: `myshop.com` или `shoes.example.com`

### 2. Настрой DNS

Зайди в панель управления доменом (где купил домен) и добавь A-запись:

```
Тип: A
Имя: @ (или myshop.com)
Значение: 34.45.43.105
TTL: 300 (или Auto)
```

Если хочешь поддомен (например `shoes.myshop.com`):

```
Тип: A
Имя: shoes
Значение: 34.45.43.105
TTL: 300
```

### 3. Запусти скрипт на VM

```bash
# Скопируй скрипт на VM
scp setup_domain.sh gcp-shoesbot:~/

# Подключись к VM
ssh gcp-shoesbot

# Запусти скрипт
chmod +x setup_domain.sh
./setup_domain.sh myshop.com
```

### 4. Подожди DNS (5-10 минут)

Проверь что DNS работает:

```bash
# На своем компьютере
ping myshop.com
# Должен показать IP: 34.45.43.105
```

### 5. Настрой HTTPS

Когда DNS заработал, на VM запусти:

```bash
sudo certbot --nginx -d myshop.com
```

Ответь на вопросы:
- Email: твой email
- Agree to terms: Yes
- Share email: No (можно)
- Redirect HTTP to HTTPS: Yes (2)

### 6. Готово!

Админка доступна: **https://myshop.com/admin/**

---

## Подробная инструкция

### Что делает скрипт:

1. **Устанавливает nginx** — веб-сервер как reverse proxy
2. **Создает конфиг** для твоего домена
3. **Настраивает проксирование** Django через nginx
4. **Обновляет Django settings** — добавляет домен в ALLOWED_HOSTS
5. **Перезапускает сервисы**

### Структура после настройки:

```
Интернет → nginx (80/443) → Django (8000)
           ↓
    https://myshop.com/admin/
```

### Файлы конфигурации:

```bash
# Nginx конфиг
/etc/nginx/sites-available/shoesbot
/etc/nginx/sites-enabled/shoesbot

# Django settings
~/shoesbot/shoessite/shoessite/settings.py
# ALLOWED_HOSTS = ['myshop.com', '34.45.43.105', ...]
```

---

## Проверка и траблшутинг

### Проверка DNS

```bash
# Должен показать 34.45.43.105
dig myshop.com +short
nslookup myshop.com
ping myshop.com
```

### Проверка nginx

```bash
# На VM
sudo nginx -t                    # Проверка конфига
sudo systemctl status nginx      # Статус
sudo tail -f /var/log/nginx/error.log  # Логи ошибок
```

### Проверка Django

```bash
# На VM
sudo systemctl status shoesdjango.service
tail -f ~/shoesbot/django.log
```

### Если не работает HTTPS

```bash
# На VM проверь сертификаты
sudo certbot certificates

# Обновить сертификат вручную
sudo certbot renew --dry-run
```

### Проверка firewall

```bash
# Порты 80 и 443 должны быть открыты
sudo ufw status
```

Если firewall активен, открой порты:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Или в Google Cloud Console:
- https://console.cloud.google.com/networking/firewalls/list
- Создай правила для портов 80 и 443

---

## Автоматическое обновление HTTPS сертификата

Certbot автоматически настроит обновление. Проверь:

```bash
# На VM
sudo systemctl status certbot.timer
```

Сертификат будет обновляться каждые 60 дней автоматически.

---

## Использование нескольких доменов

Если хочешь использовать несколько доменов (например, основной + поддомены):

### Вариант 1: Все домены на одном проекте

```bash
# Добавь все домены в настройки
./setup_domain.sh main.com
sudo certbot --nginx -d main.com -d www.main.com -d shoes.main.com
```

### Вариант 2: Разные проекты на разных доменах

Создай отдельные конфиги nginx для каждого домена.

---

## Безопасность

После настройки HTTPS:

1. ✅ Весь трафик зашифрован
2. ✅ Сертификат от Let's Encrypt (доверенный)
3. ✅ Автоматическое обновление сертификата

Рекомендации:

- Используй **надежный пароль** для Django админа
- Включи **2FA** если планируешь
- Ограничь доступ по IP если нужно (через nginx)

---

## Что дальше

После настройки домена у тебя будет:

- ✅ Красивый URL: `https://myshop.com/admin/`
- ✅ HTTPS (безопасное соединение)
- ✅ Постоянный доступ к админке
- ✅ Работает из любого места

Можно также:
- Настроить email уведомления
- Добавить Google Analytics
- Настроить резервное копирование

