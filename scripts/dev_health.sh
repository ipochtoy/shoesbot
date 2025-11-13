#!/bin/bash
# Quick health check for dev Django (port 8001)
set -e
BASE=${1:-https://pochtoy.us}

curl -k -s -o /dev/null -w 'Dev admin: HTTP %{http_code}
' "$BASE/dev/admin/"
curl -k -s -o /dev/null -w 'Dev API search: HTTP %{http_code}
' "$BASE/dev/api/ebay/search/"
