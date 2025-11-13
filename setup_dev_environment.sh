#!/bin/bash
# Setup isolated development environment
set -e

echo '📁 Создаю директорию для dev данных...'
mkdir -p /home/pochtoy/shoesbot/dev_data/media

echo '📋 Копирую production БД в dev...'
cp /home/pochtoy/shoesbot/shoessite/db.sqlite3 /home/pochtoy/shoesbot/dev_data/db.sqlite3

echo '✅ Dev окружение создано!'
echo ''
echo 'Структура dev_data:'
ls -lh /home/pochtoy/shoesbot/dev_data/
