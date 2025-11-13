# Защита от запуска нескольких копий бота

## Проблема
Telegram позволяет только **одно активное polling-подключение** на токен. Если запустить бота дважды (локально + на сервере), возникает конфликт `Conflict: terminated by other getUpdates request`, и бот не работает.

## Решение
Добавлена защита в `bot.py` через **file lock**:
- При старте бот создаёт `/tmp/shoesbot.lock`
- Если lock уже занят → бот немедленно завершается с ошибкой
- Это предотвращает случайный запуск второй копии

## Как проверить что бот запущен
```bash
# На сервере (основной)
ssh gcp-shoesbot "sudo systemctl status shoesbot.service"

# Локально (если запущен случайно)
ps aux | grep '[b]ot.py'
```

## Как остановить локальную копию
```bash
# Полностью
pkill -9 -f 'bot.py'

# Или найти PID и убить
ps aux | grep '[b]ot.py'
kill -9 <PID>
```

## Автозапуск отключён
- macOS launchd: `~/Library/LaunchAgents/com.shoesbot.plist.disabled` (переименован)
- Если нужно снова включить: `mv ~/.../com.shoesbot.plist.disabled ~/.../com.shoesbot.plist && launchctl load ...`

## Правило
⚠️ **НИКОГДА не запускай бота локально, если он работает на сервере!**  
Исключение: для тестирования останови серверного:
```bash
ssh gcp-shoesbot "sudo systemctl stop shoesbot.service"
# Тестируй локально
# После тестов:
ssh gcp-shoesbot "sudo systemctl start shoesbot.service"
```

## Как это работает в production
- Бот работает **на сервере** через `systemd` (всегда)
- Локальная копия используется **только для разработки** (когда серверная остановлена)
- File lock гарантирует, что случайный `python bot.py` на Mac не сломает production


