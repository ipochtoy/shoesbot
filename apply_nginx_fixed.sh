#!/bin/bash
# ИНСТРУКЦИЯ: Как установить исправленный nginx конфиг
# Выполни эти команды на сервере под sudo

set -e

echo "🔧 Применяю исправленный nginx конфиг..."

# 1. Backup
sudo cp /etc/nginx/sites-available/shoesbot /etc/nginx/sites-available/shoesbot.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Бекап создан"

# 2. Копируем новый конфиг
sudo cp /home/pochtoy/shoesbot/nginx-shoesbot-fixed.conf /etc/nginx/sites-available/shoesbot
echo "✅ Конфиг скопирован"

# 3. Тестируем
echo "🧪 Тестирую конфиг..."
sudo nginx -t

# 4. Перезагружаем
echo "🔄 Перезагружаю nginx..."
sudo systemctl reload nginx
echo "✅ Nginx перезагружен"

# 5. Проверяем
sleep 2
echo ""
echo "🧪 Проверяю доступность..."
curl -s -o /dev/null -w "HTTP: %{http_code}\n" http://localhost/static/admin/css/base.css
curl -s -o /dev/null -w "HTTPS: %{http_code}\n" https://pochtoy.us/static/admin/css/base.css

echo ""
echo "✅ Готово! Если видишь HTTP 200 - статика работает"

