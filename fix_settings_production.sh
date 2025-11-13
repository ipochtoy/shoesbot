#!/bin/bash
# Fix settings.py for production - исправляет проблему со слетающей версткой
set -e

SETTINGS_FILE="/home/pochtoy/shoesbot/shoessite/shoessite/settings.py"

echo '🔧 Исправляю settings.py для production...'

# Проверяем, есть ли уже production overrides
if grep -q "Production overrides - НЕ ТРОГАТЬ при rsync" "$SETTINGS_FILE"; then
    echo '✅ Production overrides уже есть в settings.py'
else
    cat >> "$SETTINGS_FILE" << 'EOFPYTHON'

# Production overrides - НЕ ТРОГАТЬ при rsync
import os
if not os.environ.get('DEV_MODE'):
    STATIC_ROOT = '/var/www/shoesbot/static/'
    STATIC_URL = '/static/'
    MEDIA_ROOT = '/home/pochtoy/shoesbot/shoessite/media'
    MEDIA_URL = '/media/'
EOFPYTHON
    echo '✅ Production overrides добавлены в settings.py'
fi

echo ''
echo 'Последние 20 строк settings.py:'
tail -20 "$SETTINGS_FILE"
