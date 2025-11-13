#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoessite.settings_dev')
import django
django.setup()

from apps.marketplaces.ebay.services.client import EbayClient

print("Testing eBay search...")
client = EbayClient()
result = client.search_comps(query='G-SHOCK GM-2110D-2AER', limit=5)
print(f'Found {len(result)} results')
if result:
    for r in result[:3]:
        title = r.get('title', 'N/A')[:60]
        price = r.get('price', 0)
        print(f"  - {title}: ${price}")
else:
    print('No results found')


