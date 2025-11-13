#!/bin/bash
# Скрипт фиксации прав доступа для nginx
# Выполняется после каждого деплоя

set -e

echo "🔒 Фиксирую права доступа для nginx..."

# Основная проблема: nginx не может читать /home/pochtoy/shoesbot/static/
# если директория shoesbot имеет права 700

# Решение: устанавливаем 755 на shoesbot чтобы www-data мог читать
chmod 755 /home/pochtoy/shoesbot

# Проверяем что статика доступна
if [ -d "/home/pochtoy/shoesbot/static" ]; then
    chmod -R 755 /home/pochtoy/shoesbot/static
    echo "✅ Права на static/ установлены"
fi

# Проверяем доступность
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/static/admin/css/base.css)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ ✅ ✅ Статика доступна (HTTP $HTTP_CODE)"
else
    echo "⚠️  Статика не доступна (HTTP $HTTP_CODE)"
    echo "Проверь nginx логи: sudo journalctl -u nginx -n 50"
fi

echo "🔒 Права зафиксированы"

