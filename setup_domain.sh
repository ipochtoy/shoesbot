#!/bin/bash
# Автоматическая настройка домена для Django админки

# Использование: ./setup_domain.sh yourdomain.com

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "❌ Укажи домен!"
    echo "Использование: ./setup_domain.sh yourdomain.com"
    exit 1
fi

echo "=========================================="
echo "Настройка домена $DOMAIN"
echo "=========================================="

# 1. Установка nginx и certbot
echo -e "\n1️⃣  Устанавливаю nginx и certbot..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 2. Создание конфига nginx
echo -e "\n2️⃣  Создаю конфиг nginx..."
sudo tee /etc/nginx/sites-available/shoesbot << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /home/pochtoy/shoesbot/shoessite/static/;
    }

    location /media/ {
        alias /home/pochtoy/shoesbot/shoessite/media/;
    }
}
EOF

# 3. Включение конфига
echo -e "\n3️⃣  Включаю конфиг..."
sudo ln -sf /etc/nginx/sites-available/shoesbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 4. Проверка конфига
echo -e "\n4️⃣  Проверяю конфиг nginx..."
sudo nginx -t

# 5. Перезапуск nginx
echo -e "\n5️⃣  Перезапускаю nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# 6. Настройка Django ALLOWED_HOSTS
echo -e "\n6️⃣  Обновляю Django settings..."
cd ~/shoesbot/shoessite

# Добавляем домен в ALLOWED_HOSTS
if ! grep -q "ALLOWED_HOSTS.*$DOMAIN" shoessite/settings.py; then
    sed -i "s/ALLOWED_HOSTS = \[\]/ALLOWED_HOSTS = ['$DOMAIN', '34.45.43.105', 'localhost', '127.0.0.1']/" shoessite/settings.py
fi

# 7. Перезапуск Django
echo -e "\n7️⃣  Перезапускаю Django..."
sudo systemctl restart shoesdjango.service

echo -e "\n=========================================="
echo "✅ Настройка завершена!"
echo "=========================================="
echo ""
echo "📋 Что дальше:"
echo ""
echo "1. Настрой DNS:"
echo "   Добавь A-запись в настройках домена:"
echo "   Тип: A"
echo "   Имя: @ (или $DOMAIN)"
echo "   Значение: 34.45.43.105"
echo "   TTL: 300"
echo ""
echo "2. Подожди 5-10 минут пока DNS обновится"
echo ""
echo "3. Проверь что домен работает:"
echo "   http://$DOMAIN/admin/"
echo ""
echo "4. Когда домен заработает, запусти настройку HTTPS:"
echo "   sudo certbot --nginx -d $DOMAIN"
echo ""
echo "5. После этого админка будет доступна:"
echo "   https://$DOMAIN/admin/"
echo ""
echo "=========================================="

