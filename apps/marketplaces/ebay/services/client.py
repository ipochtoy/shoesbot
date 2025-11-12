"""
eBay API client (stub implementation).

This is a stub/mock implementation for MVP.
In production, replace with actual eBay API calls using their SDK or REST API.
"""
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings


class EbayClient:
    """
    eBay API client with stub methods.

    All methods return mock data for MVP testing.
    Replace with real eBay API calls in production.
    """

    def __init__(self, sandbox: bool = None):
        """
        Initialize eBay client.

        Args:
            sandbox: Use sandbox environment (default from settings)
        """
        self.sandbox = sandbox if sandbox is not None else getattr(settings, 'EBAY_SANDBOX', True)
        self.app_id = getattr(settings, 'EBAY_APP_ID', '')
        self.dev_id = getattr(settings, 'EBAY_DEV_ID', '')
        self.cert_id = getattr(settings, 'EBAY_CERT_ID', '')

    def _log_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        Log API request for debugging.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Log entry dict
        """
        return {
            'timestamp': timezone.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'params': params or {},
            'sandbox': self.sandbox,
        }

    def create_or_update_listing(self, candidate) -> Dict[str, Any]:
        """
        Create or update eBay listing (STUB).

        Args:
            candidate: EbayCandidate instance

        Returns:
            Response dict with item_id and listing_url

        In production, this would call:
        - eBay Sell API: createOrReplaceInventoryItem
        - eBay Sell API: createOffer
        - eBay Sell API: publishOffer
        """
        time.sleep(0.5)  # Simulate API delay

        # Generate mock eBay item ID
        item_id = f"MOCK_{candidate.id}_{int(time.time())}"

        # Mock listing URL
        listing_url = f"https://www.ebay.com/itm/{item_id}"
        if self.sandbox:
            listing_url = f"https://sandbox.ebay.com/itm/{item_id}"

        response = {
            'success': True,
            'item_id': item_id,
            'listing_url': listing_url,
            'sku': candidate.photo_batch.sku or f"SKU_{candidate.id}",
            'status': 'ACTIVE',
            'created_at': timezone.now().isoformat(),
        }

        # Log the mock request
        log_entry = self._log_request(
            'POST',
            '/sell/inventory/v1/inventory_item',
            {
                'title': candidate.title,
                'price': str(candidate.price_final),
                'category_id': candidate.category_id,
            }
        )
        log_entry['response'] = response

        return response

    def upload_media(self, urls: List[str]) -> List[str]:
        """
        Upload media to eBay (STUB).

        Args:
            urls: List of image URLs to upload

        Returns:
            List of eBay-hosted image URLs

        In production, this would call:
        - eBay Sell API: createInventoryItemImage
        """
        time.sleep(0.2)  # Simulate upload delay

        # Return the same URLs (eBay allows external hosting)
        # In production, you might upload to eBay's servers
        return urls

    def end_listing(self, item_id: str) -> Dict[str, Any]:
        """
        End/delete eBay listing (STUB).

        Args:
            item_id: eBay item ID

        Returns:
            Response dict

        In production, this would call:
        - eBay Sell API: withdrawOffer or deleteInventoryItem
        """
        time.sleep(0.3)

        response = {
            'success': True,
            'item_id': item_id,
            'status': 'ENDED',
            'ended_at': timezone.now().isoformat(),
        }

        return response

    def update_price(self, item_id: str, new_price: float) -> Dict[str, Any]:
        """
        Update listing price (STUB).

        Args:
            item_id: eBay item ID
            new_price: New price

        Returns:
            Response dict

        In production, this would call:
        - eBay Sell API: updateOffer
        """
        time.sleep(0.2)

        response = {
            'success': True,
            'item_id': item_id,
            'new_price': new_price,
            'updated_at': timezone.now().isoformat(),
        }

        return response

    def get_business_policies(self) -> Dict[str, Any]:
        """
        Get business policies (shipping, return, payment) (STUB).

        Returns:
            Dict of policy IDs

        In production, this would call:
        - eBay Sell API: getPaymentPolicies
        - eBay Sell API: getReturnPolicies
        - eBay Sell API: getFulfillmentPolicies
        """
        return {
            'payment_policy_id': 'MOCK_PAYMENT_POLICY',
            'return_policy_id': 'MOCK_RETURN_POLICY',
            'fulfillment_policy_id': 'MOCK_SHIPPING_POLICY',
        }

    def search_categories(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for eBay categories (STUB).

        Args:
            query: Search query

        Returns:
            List of category suggestions

        In production, this would call:
        - eBay Taxonomy API: getCategorySuggestions
        """
        time.sleep(0.1)

        # Mock category suggestions based on query
        mock_categories = {
            'perfume': [
                {'category_id': '31518', 'category_name': 'Fragrances', 'category_tree_id': '0', 'leaf': True},
                {'category_id': '11854', 'category_name': 'Perfumes', 'category_tree_id': '0', 'leaf': True},
            ],
            'shoes': [
                {'category_id': '93427', 'category_name': 'Athletic Shoes', 'category_tree_id': '0', 'leaf': True},
                {'category_id': '53557', 'category_name': 'Casual Shoes', 'category_tree_id': '0', 'leaf': True},
            ],
            'electronics': [
                {'category_id': '293', 'category_name': 'Consumer Electronics', 'category_tree_id': '0', 'leaf': False},
                {'category_id': '15032', 'category_name': 'Cell Phones & Smartphones', 'category_tree_id': '0', 'leaf': True},
            ],
        }

        # Try to match query to mock data
        query_lower = query.lower()
        for key, categories in mock_categories.items():
            if key in query_lower:
                return categories

        # Default fallback
        return [
            {'category_id': '99999', 'category_name': f'General: {query}', 'category_tree_id': '0', 'leaf': True},
        ]

    def get_required_specifics(self, category_id: str) -> List[Dict[str, Any]]:
        """
        Get required item specifics for category (STUB).

        Args:
            category_id: eBay category ID

        Returns:
            List of required item specifics

        In production, this would call:
        - eBay Taxonomy API: getItemAspectsForCategory
        """
        time.sleep(0.1)

        # Mock required specifics
        # Different categories have different requirements
        common_specifics = [
            {
                'name': 'Brand',
                'required': True,
                'usage': 'REQUIRED',
                'values': [],  # Free text or suggestions
                'max_values': 1,
            },
            {
                'name': 'Condition',
                'required': True,
                'usage': 'REQUIRED',
                'values': ['New', 'Used', 'Refurbished'],
                'max_values': 1,
            },
        ]

        # Category-specific mocks
        if category_id in ['31518', '11854']:  # Perfume
            return common_specifics + [
                {'name': 'Size Type', 'required': True, 'usage': 'REQUIRED', 'values': ['Regular Size', 'Travel Size', 'Miniature'], 'max_values': 1},
                {'name': 'Volume', 'required': True, 'usage': 'REQUIRED', 'values': [], 'max_values': 1},
                {'name': 'Formulation', 'required': False, 'usage': 'RECOMMENDED', 'values': ['Eau de Parfum', 'Eau de Toilette', 'Cologne'], 'max_values': 1},
            ]

        elif category_id in ['93427', '53557']:  # Shoes
            return common_specifics + [
                {'name': 'US Shoe Size', 'required': True, 'usage': 'REQUIRED', 'values': [], 'max_values': 1},
                {'name': 'Color', 'required': True, 'usage': 'REQUIRED', 'values': [], 'max_values': 1},
                {'name': 'Style', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
            ]

        elif category_id in ['260324', '260325', '31387']:  # Watches (Men's, Women's, Unisex)
            return common_specifics + [
                {'name': 'Model', 'required': True, 'usage': 'REQUIRED', 'values': [], 'max_values': 1},
                {'name': 'Case Material', 'required': True, 'usage': 'REQUIRED', 'values': ['Stainless Steel', 'Gold', 'Silver', 'Titanium', 'Ceramic', 'Plastic'], 'max_values': 1},
                {'name': 'Band Material', 'required': True, 'usage': 'REQUIRED', 'values': ['Leather', 'Metal', 'Rubber', 'Fabric', 'Silicone'], 'max_values': 1},
                {'name': 'Movement', 'required': True, 'usage': 'REQUIRED', 'values': ['Quartz', 'Automatic', 'Mechanical', 'Solar'], 'max_values': 1},
                {'name': 'Water Resistance', 'required': False, 'usage': 'RECOMMENDED', 'values': ['30m', '50m', '100m', '200m', '300m'], 'max_values': 1},
                {'name': 'Dial Color', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
                {'name': 'Band Color', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
                {'name': 'Case Diameter', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
            ]

        else:  # Default
            return common_specifics + [
                {'name': 'Model', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
                {'name': 'Color', 'required': False, 'usage': 'RECOMMENDED', 'values': [], 'max_values': 1},
            ]

    def search_comps(
        self,
        query: Optional[str] = None,
        upc: Optional[str] = None,
        ean: Optional[str] = None,
        isbn: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for comparable listings.

        Tries real eBay search first, falls back to mock data.

        Args:
            query: Search query
            upc: UPC code
            ean: EAN code
            isbn: ISBN code
            category_id: eBay category ID
            limit: Max results

        Returns:
            List of comparable items
        """
        # Build search query - prioritize product codes
        search_term = upc or ean or isbn or query
        
        if not search_term:
            return []
        
        # Try real eBay search via scraping
        try:
            comps = self._scrape_ebay_search(search_term, limit)
            if comps:
                return comps
        except Exception as e:
            print(f"eBay scraping error: {e}")
        
        # Fallback to mock data for testing
        import random
        base_price = random.uniform(20, 100)
        comps = []

        for i in range(min(limit, 10)):
            price_variation = random.uniform(0.85, 1.15)
            price = round(base_price * price_variation, 2)

            comps.append({
                'item_id': f'MOCK_{i}',
                'title': f'{search_term} - Similar Item {i+1}',
                'price': price,
                'condition': random.choice(['NEW', 'USED_EXCELLENT', 'USED_GOOD']),
                'shipping_cost': random.choice([0, 4.99]),
                'seller_rating': random.randint(95, 100),
                'location': 'US',
                'url': f'https://www.ebay.com/sch/i.html?_nkw={search_term}',
                'sold_date': None,
                'note': 'Mock data - real eBay search not available',
            })

        return comps
    
    def _scrape_ebay_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape eBay search results for comparable items.
        
        Args:
            query: Search term
            limit: Max results
            
        Returns:
            List of items with prices
        """
        import requests
        from bs4 import BeautifulSoup
        import re
        
        comps = []
        
        # Build eBay search URL - sold/completed listings for real market data
        params = {
            '_nkw': query,
            '_sacat': '0',  # All categories
            'LH_Sold': '1',  # Sold listings
            'LH_Complete': '1',  # Completed listings
            '_sop': '13',  # Sort by recently sold
            'rt': 'nc',
        }
        
        url = 'https://www.ebay.com/sch/i.html'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if not response.ok:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find item listings
            items = soup.find_all('li', {'class': 's-item'})[:limit]
            
            for item in items:
                try:
                    # Extract title
                    title_elem = item.find('div', {'class': 's-item__title'})
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    if not title or 'Shop on eBay' in title:
                        continue
                    
                    # Extract price
                    price_elem = item.find('span', {'class': 's-item__price'})
                    price_text = price_elem.get_text(strip=True) if price_elem else ''
                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                    price = float(price_match.group(1).replace(',', '')) if price_match else 0
                    
                    if price == 0:
                        continue
                    
                    # Extract item ID and URL
                    link_elem = item.find('a', {'class': 's-item__link'})
                    item_url = link_elem.get('href', '') if link_elem else ''
                    item_id_match = re.search(r'/itm/(\d+)', item_url)
                    item_id = item_id_match.group(1) if item_id_match else ''
                    
                    # Extract shipping
                    shipping_elem = item.find('span', {'class': 's-item__shipping'})
                    shipping_text = shipping_elem.get_text(strip=True) if shipping_elem else ''
                    shipping_cost = 0 if 'Free' in shipping_text else 4.99
                    
                    # Extract condition
                    condition_elem = item.find('span', {'class': 'SECONDARY_INFO'})
                    condition_text = condition_elem.get_text(strip=True) if condition_elem else 'Used'
                    condition = self._map_condition_from_text(condition_text)
                    
                    comps.append({
                        'item_id': item_id,
                        'title': title[:100],
                        'price': price,
                        'condition': condition,
                        'shipping_cost': shipping_cost,
                        'seller_rating': 98,  # Default good rating
                        'location': 'US',
                        'url': item_url,
                        'sold_date': 'recently',
                        'note': 'Real eBay sold listing',
                    })
                    
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            return comps
            
        except Exception as e:
            print(f"eBay scraping failed: {e}")
            return []
    
    def _map_condition_from_text(self, text: str) -> str:
        """Map eBay condition text to enum."""
        text_lower = text.lower()
        if 'new' in text_lower:
            return 'NEW'
        elif 'excellent' in text_lower:
            return 'USED_EXCELLENT'
        elif 'very good' in text_lower or 'like new' in text_lower:
            return 'USED_VERY_GOOD'
        elif 'good' in text_lower:
            return 'USED_GOOD'
        elif 'acceptable' in text_lower:
            return 'USED_ACCEPTABLE'
        else:
            return 'USED_GOOD'

    def fetch_orders(self, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetch recent orders (STUB).

        Args:
            since: Fetch orders since this datetime

        Returns:
            List of orders

        In production, this would call:
        - eBay Sell API: getOrders
        """
        time.sleep(0.2)

        # Return empty orders for stub
        # In production, this would return actual order data
        return []

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh OAuth access token (STUB).

        Args:
            refresh_token: Refresh token

        Returns:
            New token data

        In production, this would call:
        - eBay OAuth API: /identity/v1/oauth2/token
        """
        time.sleep(0.2)

        # Mock new token
        return {
            'access_token': f'MOCK_ACCESS_TOKEN_{int(time.time())}',
            'expires_at': timezone.now() + timedelta(hours=2),
            # Refresh token may or may not be rotated depending on eBay settings
        }
