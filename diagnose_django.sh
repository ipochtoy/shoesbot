#!/bin/bash
# Диагностика проблем с Django на VM

echo "========================================"
echo "ДИАГНОСТИКА DJANGO UPLOAD"
echo "========================================"

echo -e "\n1️⃣  === СТАТУС СЕРВИСОВ ==="
echo "Bot service:"
sudo systemctl is-active shoesbot.service
echo "Django service:"
sudo systemctl is-active shoesdjango.service

echo -e "\n2️⃣  === ПОРТ DJANGO ==="
if sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Django слушает на порту 8000"
    sudo lsof -i :8000 | head -3
else
    echo "❌ Django НЕ слушает на порту 8000!"
fi

echo -e "\n3️⃣  === КОНФИГУРАЦИЯ .env ==="
if [ -f ~/shoesbot/.env ]; then
    if grep -q "DJANGO_API_URL" ~/shoesbot/.env; then
        echo "✅ DJANGO_API_URL найден:"
        grep DJANGO ~/shoesbot/.env
    else
        echo "❌ DJANGO_API_URL НЕ НАЙДЕН в .env!"
        echo "Добавь: DJANGO_API_URL=http://127.0.0.1:8000/photos/api/upload-batch/"
    fi
else
    echo "❌ Файл .env не найден!"
fi

echo -e "\n4️⃣  === ДОСТУПНОСТЬ DJANGO ==="
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/admin/ | grep -q "200\|302"; then
    echo "✅ Django отвечает на запросы"
else
    echo "❌ Django НЕ отвечает!"
fi

echo -e "\n5️⃣  === ПОСЛЕДНИЕ ОШИБКИ В ЛОГАХ БОТА ==="
if [ -f ~/shoesbot/bot.log ]; then
    echo "Ищу упоминания django_upload..."
    tail -100 ~/shoesbot/bot.log | grep -i "django_upload" | tail -5
    if [ $? -ne 0 ]; then
        echo "(нет упоминаний django_upload в последних 100 строках)"
    fi
else
    echo "❌ bot.log не найден"
fi

echo -e "\n6️⃣  === ПОСЛЕДНИЕ ОШИБКИ В ЛОГАХ DJANGO ==="
if [ -f ~/shoesbot/django.log ]; then
    echo "Последние ошибки:"
    tail -50 ~/shoesbot/django.log | grep -i "error\|exception" | tail -3
    if [ $? -ne 0 ]; then
        echo "(нет ошибок в последних 50 строках)"
    fi
else
    echo "❌ django.log не найден"
fi

echo -e "\n========================================"
echo "РЕКОМЕНДАЦИИ:"
echo "========================================"

# Проверки и рекомендации
all_ok=true

if ! sudo systemctl is-active shoesdjango.service > /dev/null 2>&1; then
    echo "🔧 Запусти Django: sudo systemctl restart shoesdjango.service"
    all_ok=false
fi

if ! sudo lsof -i :8000 > /dev/null 2>&1; then
    echo "🔧 Django не слушает на порту 8000"
    all_ok=false
fi

if ! grep -q "DJANGO_API_URL" ~/shoesbot/.env 2>/dev/null; then
    echo "🔧 Добавь в .env: DJANGO_API_URL=http://127.0.0.1:8000/photos/api/upload-batch/"
    all_ok=false
fi

if $all_ok; then
    echo "✅ Всё выглядит OK!"
    echo "Если товары всё равно не загружаются, отправь фото в бот и пришли:"
    echo "  tail -50 ~/shoesbot/bot.log"
    echo "  tail -50 ~/shoesbot/django.log"
fi

echo -e "\nДля перезапуска сервисов:"
echo "  sudo systemctl restart shoesbot.service"
echo "  sudo systemctl restart shoesdjango.service"

