#!/bin/bash
# Открытие порта 8000 в Google Cloud Firewall

echo "Открываю порт 8000 для Django админки..."

gcloud compute firewall-rules create allow-django \
    --allow tcp:8000 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow Django admin access" \
    --direction INGRESS

echo "✅ Порт 8000 открыт"
echo "⚠️  ВНИМАНИЕ: Админка Django теперь доступна из интернета!"
echo "   Убедись что у тебя надежный пароль админа"
echo ""
echo "Админка: http://34.45.43.105:8000/admin/"

