#!/bin/bash
# Полная проверка системы shoesbot

echo "═══════════════════════════════════════════"
echo "   ПОЛНАЯ ПРОВЕРКА SHOESBOT"
echo "═══════════════════════════════════════════"

ERRORS=0

echo ""
echo "🧪 Запуск тестов..."
if ! /home/pochtoy/shoesbot/run_tests.sh; then
    ERRORS=$((ERRORS+1))
fi

echo ""
echo "🔧 Проверка сервисов..."
for service in shoesbot shoesdjango shoesdjango-dev shoesbot-watchdog; do
    if systemctl is-active --quiet ${service}.service 2>/dev/null; then
        echo "  ✅ ${service}.service: running"
    else
        echo "  ⚠️  ${service}.service: not running"
    fi
done

echo ""
echo "🌐 Проверка HTTP..."
for port in 8000 8001; do
    CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${port}/admin/ || echo '000')
    if [ "$CODE" == "200" ] || [ "$CODE" == "302" ]; then
        echo "  ✅ Port ${port}: HTTP ${CODE}"
    else
        echo "  ❌ Port ${port}: HTTP ${CODE}"
        ERRORS=$((ERRORS+1))
    fi
done

echo ""
echo "🎨 Проверка статики..."
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/static/admin/css/base.css)
if [ "$CODE" == "200" ] || [ "$CODE" == "304" ]; then
    echo "  ✅ Static files: OK"
else
    echo "  ❌ Static files: FAIL (HTTP $CODE)"
    ERRORS=$((ERRORS+1))
fi

echo ""
echo "📸 Проверка media..."
PHOTO_COUNT=$(find /home/pochtoy/shoesbot/shoessite/media/photos -type f 2>/dev/null | wc -l || echo 0)
echo "  📁 Local photos: $PHOTO_COUNT files"

echo ""
echo "💽 Дисковое пространство:"
df -h /home | tail -1

echo ""
echo "📋 Недавние ошибки в логах (last 3):"
echo "  Bot errors:"
grep -i error /home/pochtoy/shoesbot/bot.log 2>/dev/null | tail -3 || echo "    (no errors)"
echo "  Django errors:"
grep -i error /home/pochtoy/shoesbot/django.log 2>/dev/null | tail -3 || echo "    (no errors)"

echo ""
echo "📝 Git status:"
cd /home/pochtoy/shoesbot
echo "  Current commit: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current)"

echo ""
echo "═══════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo "✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ"
    echo "═══════════════════════════════════════════"
    exit 0
else
    echo "❌ НАЙДЕНО ОШИБОК: $ERRORS"
    echo "═══════════════════════════════════════════"
    exit 1
fi
