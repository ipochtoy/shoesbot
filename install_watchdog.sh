#!/bin/bash
# Install watchdog service
set -e

echo '🐕 Устанавливаю watchdog сервис...'

echo '📋 Копирую systemd сервис...'
sudo cp /home/pochtoy/shoesbot/systemd/shoesbot-watchdog.service /etc/systemd/system/

echo '🔄 Перезагружаю systemd...'
sudo systemctl daemon-reload

echo '✅ Включаю автозапуск watchdog...'
sudo systemctl enable shoesbot-watchdog.service

echo '🚀 Запускаю watchdog...'
sudo systemctl start shoesbot-watchdog.service

echo '⏳ Ждем 2 секунды...'
sleep 2

echo '📊 Статус watchdog:'
sudo systemctl status shoesbot-watchdog.service --no-pager

echo ''
echo '✅ Watchdog установлен и запущен!'
echo 'Логи: /home/pochtoy/shoesbot/watchdog.log'
