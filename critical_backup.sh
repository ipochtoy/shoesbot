#!/bin/bash
# Critical backup script - БД, медиа, код
set -e

DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /home/pochtoy/backups/critical

echo '📦 Бекап БД...'
cp /home/pochtoy/shoesbot/shoessite/db.sqlite3 /home/pochtoy/backups/critical/db-${DATE}.sqlite3

echo '📸 Бекап медиа...'
tar -czf /home/pochtoy/backups/critical/media-${DATE}.tar.gz -C /home/pochtoy/shoesbot/shoessite media/

echo '💾 Бекап кода...'
tar -czf /home/pochtoy/backups/critical/code-${DATE}.tar.gz -C /home/pochtoy shoesbot/ --exclude='shoesbot/.venv' --exclude='shoesbot/shoessite/media'

echo '✅ Бекапы созданы:'
ls -lh /home/pochtoy/backups/critical/ | tail -5
