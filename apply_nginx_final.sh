#!/bin/bash
# Final script to apply nginx config - run this on server with sudo password
# Or run these commands manually:

echo "📋 To apply nginx config, run these commands on the server:"
echo ""
echo "sudo cp /tmp/shoesbot_nginx_temp.conf /etc/nginx/sites-available/shoesbot"
echo "sudo nginx -t"
echo "sudo systemctl reload nginx"
echo ""
echo "Then test: https://pochtoy.us/dev/admin/"

