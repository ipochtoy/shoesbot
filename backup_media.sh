#!/bin/bash
#
# Daily backup of media files and database
# Add to crontab: 0 3 * * * /home/pochtoy/shoesbot/backup_media.sh
#

set -e

BACKUP_DIR="/home/pochtoy/backups"
DATE=$(date +%Y%m%d)
MEDIA_DIR="/home/pochtoy/shoesbot/shoessite/media"
DB_FILE="/home/pochtoy/shoesbot/shoessite/db.sqlite3"

echo "🗄️ Starting backup at $(date)"

# Create backup directories
mkdir -p "$BACKUP_DIR/media"
mkdir -p "$BACKUP_DIR/db"

# Backup media files
echo "📸 Backing up media files..."
rsync -av --delete "$MEDIA_DIR/" "$BACKUP_DIR/media/media-$DATE/" 2>&1 | tail -5

# Backup database (используем sqlite3 .backup для безопасности)
echo "💾 Backing up database..."
if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/db/db-$DATE.sqlite3'"
else
    cp "$DB_FILE" "$BACKUP_DIR/db/db-$DATE.sqlite3"
fi

# Keep only last 7 days of backups
echo "🧹 Cleaning old backups..."
find "$BACKUP_DIR/media" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
find "$BACKUP_DIR/db" -type f -mtime +7 -delete 2>/dev/null || true

# Check disk usage
USAGE=$(df -h /home | tail -1 | awk '{print $5}' | sed 's/%//')
echo "💽 Disk usage: $USAGE%"

if [ "$USAGE" -gt 85 ]; then
    echo "⚠️  WARNING: Disk usage above 85%!"
    # Could send alert to Telegram here
fi

echo "✅ Backup complete at $(date)"
echo "📊 Backup sizes:"
du -sh "$BACKUP_DIR/media/media-$DATE" 2>/dev/null || echo "  Media: new backup"
du -sh "$BACKUP_DIR/db/db-$DATE.sqlite3" 2>/dev/null || echo "  DB: new backup"

