#!/bin/bash
# Тестируем бота ПЕРЕД деплоем

echo "🧪 Тестирую бота..."

cd ~/Projects/shoesbot

# Активируем виртуальное окружение если есть
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Проверяем что bot.py запускается
echo "Проверяю bot.py..."
timeout 5 python bot.py > /dev/null 2>&1 &
PID=$!
sleep 2

if ps -p $PID > /dev/null; then
    echo "✅ Бот стартует без ошибок"
    kill $PID 2>/dev/null
else
    echo "❌ ОШИБКА: Бот не запускается!"
    echo "НЕ ДЕПЛОЙ! Сначала исправь ошибки."
    exit 1
fi

# Проверяем импорты
echo "Проверяю импорты..."
python -c "from shoesbot.telegram_bot import build_app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ telegram_bot.py OK"
else
    echo "❌ ОШИБКА в telegram_bot.py"
    exit 1
fi

python -c "from shoesbot.pipeline import DecoderPipeline" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ pipeline.py OK"
else
    echo "❌ ОШИБКА в pipeline.py"
    exit 1
fi

echo ""
echo "✅ ВСЕ ТЕСТЫ ПРОШЛИ!"
echo "Можно деплоить."

