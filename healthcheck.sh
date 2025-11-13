#!/bin/bash
# Health check script for all services

ERRORS=0

# Проверка бота
if ! systemctl is-active --quiet shoesbot.service; then
    echo "❌ Bot is NOT running"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Bot is running"
fi

# Проверка Django production
if ! systemctl is-active --quiet shoesdjango.service; then
    echo "❌ Django prod is NOT running"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Django prod is running"
fi

# HTTP проверка Django
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/ || echo '000')
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo "❌ Django HTTP check failed (code: $HTTP_CODE)"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Django HTTP check OK (code: $HTTP_CODE)"
fi

# Проверка дискового пространства
DISK_USAGE=$(df -h /home | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "⚠️  Disk usage: ${DISK_USAGE}%"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All systems operational"
    exit 0
else
    echo "❌ Found $ERRORS errors"
    exit 1
fi
