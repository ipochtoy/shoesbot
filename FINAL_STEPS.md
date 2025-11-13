# Финальные шаги - выполни на сервере

## 1. Подключись к серверу
```bash
ssh gcp-shoesbot
cd /home/pochtoy/shoesbot
```

## 2. Установи watchdog (автовосстановление)
```bash
sudo ./install_watchdog.sh
```

## 3. Исправь статику (CSS в админке)
```bash
sudo mkdir -p /var/www/shoesbot/static
sudo chown -R pochtoy:pochtoy /var/www/shoesbot
cd shoessite
../.venv/bin/python manage.py collectstatic --noinput
cd ..
sudo systemctl restart shoesdjango
```

## 4. Запусти dev Django (опционально)
```bash
sudo systemctl start shoesdjango-dev
sudo systemctl enable shoesdjango-dev
```

## 5. Проверь что всё работает
```bash
./full_check.sh
```

## 6. Открой админку в браузере
https://pochtoy.us/admin/
- Логин: admin
- Пароль: admin123

Проверь что CSS грузится, фото на месте.

---

# Готово! 🚀

Теперь у тебя:
- ✅ Бот защищен от падений (watchdog)
- ✅ Автоматические бекапы
- ✅ Безопасный деплой с автотестами
- ✅ DEV/PROD изоляция
- ✅ Мониторинг и healthcheck

Используй:
- `./deploy.sh` - для деплоя
- `./full_check.sh` - для проверки системы
- `./healthcheck.sh` - быстрая проверка
- См. `ОПЕРАЦИИ.md` - полный список команд

