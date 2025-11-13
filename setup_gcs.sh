#!/bin/bash
# Setup Google Cloud Storage support
set -e

echo '📦 Устанавливаю библиотеки для GCS...'
cd /home/pochtoy/shoesbot
.venv/bin/pip install django-storages[google] google-cloud-storage

echo '🔧 Обновляю .env файл...'
# Добавляем USE_GCS если его еще нет
if ! grep -q 'USE_GCS' /home/pochtoy/shoesbot/.env 2>/dev/null; then
    echo 'USE_GCS=false' >> /home/pochtoy/shoesbot/.env
    echo '  ✅ Добавлен USE_GCS=false в .env'
else
    echo '  ℹ️  USE_GCS уже есть в .env'
fi

echo ''
echo '✅ GCS библиотеки установлены!'
echo ''
echo 'Для включения GCS измените в .env:'
echo '  USE_GCS=true'
echo ''
echo 'Для работы GCS также нужно:'
echo '  1. Создать bucket в Google Cloud Storage'
echo '  2. Настроить credentials (service account key)'
echo '  3. Установить GOOGLE_APPLICATION_CREDENTIALS в .env'
