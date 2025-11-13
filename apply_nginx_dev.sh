#!/bin/bash
# Script to apply nginx config for dev Django
# Run this on the server: bash apply_nginx_dev.sh

CONFIG_FILE='/etc/nginx/sites-available/shoesbot'
TEMP_FILE='/tmp/shoesbot_nginx_temp.conf'

cat > "$TEMP_FILE" << 'ENDOFCONFIG'
server {
    server_name pochtoy.us www.pochtoy.us;

    # Dev Django on /dev/ path (must be before location /)
    location /dev/ {
        rewrite ^/dev/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/pochtoy/shoesbot/static/;
    }

    location /media/ {
        alias /home/pochtoy/shoesbot/shoessite/media/;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/pochtoy.us/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/pochtoy.us/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
server {
    if ($host = www.pochtoy.us) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    if ($host = pochtoy.us) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name pochtoy.us www.pochtoy.us;
    return 404; # managed by Certbot
}
ENDOFCONFIG

echo "✅ Config created in $TEMP_FILE"
echo "📋 Run these commands:"
echo "   sudo cp $TEMP_FILE $CONFIG_FILE"
echo "   sudo nginx -t"
echo "   sudo systemctl reload nginx"

