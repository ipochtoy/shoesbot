#!/bin/bash
# Деплой на VM прямо из локального компьютера

set -e  # Остановиться при ошибке

echo "🚀 Деплой shoesbot на VM..."
echo ""

# 1. Коммитим и пушим изменения
echo "📦 Коммичу изменения..."
git add .

# Если есть изменения - коммитим
if ! git diff-index --quiet HEAD --; then
    read -p "💬 Описание коммита: " commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="Update $(date +%Y-%m-%d)"
    fi
    git commit -m "$commit_msg"
    echo "✅ Изменения закоммичены"
else
    echo "ℹ️  Нет изменений для коммита"
fi

# 2. Пушим в GitHub
echo ""
echo "📤 Пушу в GitHub..."
git push origin main
echo "✅ Код в GitHub"

# 3. Деплоим на VM
echo ""
echo "🔄 Деплою на VM..."
ssh gcp-shoesbot 'cd ~/shoesbot && git pull origin main && chmod +x deploy.sh && ./deploy.sh'

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "🌐 Админка: https://pochtoy.us/admin/"
echo "🤖 Бот: отправь /ping в Telegram"

