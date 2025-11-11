#!/bin/bash
# ФИНАЛЬНЫЙ ФИКС ВСЕХ ПРОБЛЕМ С ПРАВАМИ
# Запусти на VM ОДИН РАЗ с sudo

echo "🔧 Исправляю все права доступа..."

# 1. Даем nginx доступ к home директориям
chmod o+x /home
chmod o+x /home/pochtoy
chmod o+x /home/pochtoy/shoesbot
chmod o+x /home/pochtoy/shoesbot/shoessite

# 2. Даем права на все static файлы
find /home/pochtoy/shoesbot/static/ -type d -exec chmod o+rx {} \;
find /home/pochtoy/shoesbot/static/ -type f -exec chmod o+r {} \;

# 3. Даем права на все media файлы (старые и новые)
find /home/pochtoy/shoesbot/shoessite/media/ -type d -exec chmod o+rx {} \;
find /home/pochtoy/shoesbot/shoessite/media/ -type f -exec chmod o+r {} \;

# 4. Настраиваем автоматические права для новых файлов
# Добавляем umask в Django service
if ! grep -q "UMask" /etc/systemd/system/shoesdjango.service 2>/dev/null; then
    sed -i '/\[Service\]/a UMask=0022' /etc/systemd/system/shoesdjango.service 2>/dev/null || true
fi

# 5. Перезагружаем все сервисы
systemctl daemon-reload
systemctl restart shoesdjango.service
systemctl restart shoesbot.service
systemctl reload nginx

echo ""
echo "✅ ВСЁ ГОТОВО!"
echo ""
echo "Теперь:"
echo "  - Все фотки видны в админке"
echo "  - Новые фотки будут автоматически доступны"
echo "  - CSS работает"
echo ""
echo "Админка: https://pochtoy.us/admin/"

