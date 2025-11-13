#!/bin/bash
# Install git hooks
set -e

echo '🪝 Устанавливаю git hooks...'

# Копируем hooks в .git/hooks/
cp /home/pochtoy/shoesbot/git-hooks/post-merge /home/pochtoy/shoesbot/.git/hooks/post-merge

# Делаем исполняемыми
chmod +x /home/pochtoy/shoesbot/.git/hooks/post-merge

echo '✅ Git hooks установлены!'
echo ''
echo 'Установленные hooks:'
ls -la /home/pochtoy/shoesbot/.git/hooks/ | grep -v sample
