#!/bin/bash
#
# Setup automatic backups for media and database
#

set -e

echo "📦 Setting up automatic backups..."

# Add to crontab (run daily at 3 AM)
CRON_JOB="0 3 * * * /home/pochtoy/shoesbot/backup_media.sh >> /home/pochtoy/shoesbot/backup.log 2>&1"

# Check if already exists
if crontab -l 2>/dev/null | grep -q "backup_media.sh"; then
    echo "✅ Backup job already exists in crontab"
else
    echo "➕ Adding backup job to crontab..."
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Backup job added"
fi

# Create backup directories
mkdir -p /home/pochtoy/backups/media
mkdir -p /home/pochtoy/backups/db

# Run first backup now
echo "🚀 Running initial backup..."
/home/pochtoy/shoesbot/backup_media.sh

echo "✅ Backups configured!"
echo ""
echo "📋 Backup schedule:"
echo "  - Daily at 3 AM"
echo "  - Keeps last 7 days"
echo "  - Location: /home/pochtoy/backups/"
echo ""
echo "🔍 Check backup logs: tail -f /home/pochtoy/shoesbot/backup.log"

