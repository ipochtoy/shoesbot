#!/bin/bash
# Watchdog для автоматического восстановления сервисов

LOG_FILE="/home/pochtoy/shoesbot/watchdog.log"

while true; do
    # Проверка бота (СВЯЩЕННАЯ КОРОВА - всегда должен работать!)
    if ! systemctl is-active --quiet shoesbot.service; then
        echo "$(date): Bot down, restarting..." >> $LOG_FILE
        sudo systemctl start shoesbot.service
    fi

    # Проверка Django production
    if ! systemctl is-active --quiet shoesdjango.service; then
        echo "$(date): Django down, restarting..." >> $LOG_FILE
        sudo systemctl start shoesdjango.service
    fi

    # HTTP проверка Django
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/ || echo '000')
    if [ "$HTTP_CODE" == "000" ] || [ "$HTTP_CODE" == "502" ] || [ "$HTTP_CODE" == "503" ]; then
        echo "$(date): Django not responding (HTTP $HTTP_CODE), restarting..." >> $LOG_FILE
        sudo systemctl restart shoesdjango.service
    fi

    # Ждем 60 секунд перед следующей проверкой
    sleep 60
done
