#!/bin/bash
# Проверка здоровья бота (запускается каждые 5 минут автоматически)

TELEGRAM_BOT_TOKEN="${BOT_TOKEN}"
ADMIN_CHAT_ID="${ADMIN_CHAT_ID:-492304809}"  # Твой Telegram ID

check_service() {
    ssh gcp-shoesbot "sudo systemctl is-active $1" 2>/dev/null
}

send_alert() {
    local message="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${ADMIN_CHAT_ID}" \
            -d text="🚨 АЛЕРТ: ${message}" \
            -d parse_mode="HTML" > /dev/null
    fi
}

# Проверка бота
BOT_STATUS=$(check_service shoesbot.service)
if [ "$BOT_STATUS" != "active" ]; then
    echo "❌ БОТ НЕ РАБОТАЕТ!"
    send_alert "БОТ УПАЛ! Статус: $BOT_STATUS"
    exit 1
fi

# Проверка Django
DJANGO_STATUS=$(check_service shoesdjango.service)
if [ "$DJANGO_STATUS" != "active" ]; then
    echo "⚠️ Django не работает (но бот ОК)"
    send_alert "Django упал, но бот работает. Статус: $DJANGO_STATUS"
fi

# Проверка последних логов на ошибки
RECENT_ERRORS=$(ssh gcp-shoesbot 'tail -50 ~/shoesbot/bot.log | grep -i "error\|exception\|traceback" | wc -l' 2>/dev/null)
if [ "$RECENT_ERRORS" -gt 5 ]; then
    echo "⚠️ Много ошибок в логах ($RECENT_ERRORS)"
    send_alert "В логах бота обнаружено $RECENT_ERRORS ошибок за последние 50 строк"
fi

echo "✅ Бот работает нормально"
echo "   Django: $DJANGO_STATUS"
echo "   Ошибок в логах: $RECENT_ERRORS"

