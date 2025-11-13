#!/bin/bash
# Setup nginx for dev Django on port 8001
# Run with: sudo ./setup_nginx_dev.sh

set -e

CONF_FILE="/etc/nginx/sites-available/django-dev"
TMP_FILE="/tmp/django-dev.conf"

if [ ! -f "$TMP_FILE" ]; then
    echo "❌ Config file not found at $TMP_FILE"
    exit 1
fi

echo "📋 Copying nginx config..."
sudo cp "$TMP_FILE" "$CONF_FILE"

echo "🔗 Creating symlink..."
sudo ln -sf "$CONF_FILE" /etc/nginx/sites-enabled/django-dev

echo "✅ Testing nginx config..."
sudo nginx -t

echo "🔄 Reloading nginx..."
sudo systemctl reload nginx

echo "✅ Nginx configured for dev Django on port 8001"

