#!/bin/bash
# Commit current stable state to git
set -e

cd /home/pochtoy/shoesbot

echo '📝 Добавляю все изменения в git...'
git add -A

echo '💾 Создаю коммит...'
git commit -m 'STABLE: Working state before refactoring' || echo 'Nothing to commit'

echo '📤 Пушу на GitHub...'
git push origin main

echo '✅ Git состояние зафиксировано'
