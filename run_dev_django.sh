#!/bin/bash
# Start dev Django on port 8001

cd ~/shoesbot/shoessite
source ../.venv/bin/activate

# Copy production DB if dev DB doesn't exist
if [ ! -f dev_db.sqlite3 ]; then
    echo "📋 Copying production DB..."
    cp db.sqlite3 dev_db.sqlite3
    echo "✅ Dev DB created"
fi

# Start dev server with auto-reload
echo "🚀 Starting DEV Django on port 8001..."
python manage.py runserver 0.0.0.0:8001 --settings=shoessite.settings_dev

