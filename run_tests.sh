#!/bin/bash
# Запуск всех тестов
set -e

echo "🧪 Running tests..."
cd /home/pochtoy/shoesbot

echo ""
echo "📱 Bot tests:"
.venv/bin/python test_bot_import.py

echo ""
echo "🌐 Django tests:"
cd shoessite
../.venv/bin/python manage.py test --verbosity=1
cd ..

echo ""
echo "🏥 Health check:"
./healthcheck.sh

echo ""
echo "✅ All tests passed!"
