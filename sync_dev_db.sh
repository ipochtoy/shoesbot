#!/bin/bash
# Sync dev DB with production data

cd ~/shoesbot/shoessite
echo "⚠️  Заменяю dev БД копией production..."
cp db.sqlite3 dev_db.sqlite3
echo "✅ Dev БД обновлена"

