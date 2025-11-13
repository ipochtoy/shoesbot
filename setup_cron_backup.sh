#!/bin/bash
# Setup cron job for automatic backups
set -e

echo '⏰ Настраиваю автоматические бекапы...'

# Проверяем есть ли уже задача в cron
if crontab -l 2>/dev/null | grep -q backup_media.sh; then
    echo '  ℹ️  Cron задача уже существует'
else
    # Добавляем новую задачу (каждый день в 3:00 AM)
    (crontab -l 2>/dev/null; echo '0 3 * * * /home/pochtoy/shoesbot/backup_media.sh >> /home/pochtoy/backups/backup.log 2>&1') | crontab -
    echo '  ✅ Cron задача добавлена'
fi

echo ''
echo 'Текущие cron задачи:'
crontab -l | grep backup || echo '(нет задач с backup)'

echo ''
echo '✅ Автоматические бекапы настроены!'
echo 'Бекапы будут выполняться каждый день в 3:00 AM'
