#!/bin/bash
# Install systemd service for dev Django
set -e

echo '📋 Копирую systemd сервис...'
sudo cp /home/pochtoy/shoesbot/systemd/shoesdjango-dev.service /etc/systemd/system/

echo '🔄 Перезагружаю systemd...'
sudo systemctl daemon-reload

echo '✅ Включаю автозапуск dev сервиса...'
sudo systemctl enable shoesdjango-dev.service

echo '🚀 Запускаю dev Django...'
sudo systemctl restart shoesdjango-dev.service

echo '⏳ Ждем 3 секунды...'
sleep 3

echo '📊 Статус dev сервиса:'
sudo systemctl status shoesdjango-dev.service --no-pager

echo ''
echo '✅ Dev Django сервис установлен и запущен на порту 8001'
