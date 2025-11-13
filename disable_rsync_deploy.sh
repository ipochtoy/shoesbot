#!/bin/bash
# Disable dangerous rsync deployment
set -e

echo '🔒 Отключаю rsync deployment...'

if [ -f /home/pochtoy/shoesbot/deploy_from_local.sh ]; then
    mv /home/pochtoy/shoesbot/deploy_from_local.sh /home/pochtoy/shoesbot/deploy_from_local.sh.DISABLED
    echo '  ✅ deploy_from_local.sh переименован в .DISABLED'
else
    echo '  ℹ️  deploy_from_local.sh уже отключен или не найден'
fi

echo ''
echo '✅ Rsync deployment отключен!'
echo ''
echo 'Используй только безопасный деплой через Git:'
echo '  cd ~/shoesbot && ./deploy.sh'
