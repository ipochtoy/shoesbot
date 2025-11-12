"""
eBay API client (stub implementation).

This is a stub/mock implementation for MVP.
In production, replace with actual eBay API calls using their SDK or REST API.
"""
import time
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

# Try to load .env if not already loaded
try:
    from dotenv import load_dotenv
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except:
    pass


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
        limit: int = 20,
        sold_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for comparable listings using eBay Finding API.

        Args:
            query: Search query
            upc: UPC code
            ean: EAN code
            isbn: ISBN code
            category_id: eBay category ID
            limit: Max results
            sold_only: Search only sold/completed listings

        Returns:
            List of comparable items
        """
        import requests
        import os
        
        # Build search query - используем keywords вместо фильтров по кодам
        # Это позволяет находить товары даже если Model не заполнен продавцом
        search_terms = []
        if query:
            search_terms.append(query)
        if upc:
            search_terms.append(upc)
        if ean:
            search_terms.append(ean)
        if isbn:
            search_terms.append(isbn)
        
        if not search_terms:
            return []
        
        # Объединяем все термины для поиска
        search_term = ' '.join(search_terms[:5])  # Максимум 5 терминов
        
        # Get eBay App ID - try multiple sources
        ebay_app_id = getattr(settings, 'EBAY_APP_ID', '') or os.getenv('EBAY_APP_ID') or os.environ.get('EBAY_APP_ID', '')
        
        if not ebay_app_id:
            print(f"[EbayClient] No eBay App ID found (checked settings.EBAY_APP_ID={getattr(settings, 'EBAY_APP_ID', '')}, os.getenv={os.getenv('EBAY_APP_ID')}), using fallback scraping")
            try:
                comps = self._scrape_ebay_search(search_term, limit)
                if comps:
                    return comps
            except Exception as e:
                print(f"[EbayClient] eBay scraping error: {e}")
            return []
        
        # Use eBay Finding API - НЕ используем фильтры по UPC/EAN, только keywords
        # Это позволяет находить товары даже если продавцы не заполнили Model
        try:
            url = 'https://svcs.ebay.com/services/search/FindingService/v1'
            params = {
                'OPERATION-NAME': 'findItemsAdvanced',
                'SERVICE-VERSION': '1.0.0',
                'SECURITY-APPNAME': ebay_app_id,
                'RESPONSE-DATA-FORMAT': 'JSON',
                'REST-PAYLOAD': '',
                'keywords': search_term,
                'paginationInput.entriesPerPage': str(min(limit, 100)),
                'sortOrder': 'PricePlusShippingLowest',
            }
            
            # Add category filter if provided
            if category_id:
                params['categoryId'] = category_id
            
            # НЕ используем фильтры по UPC/EAN - они слишком строгие
            # Вместо этого ищем по keywords, что находит товары даже без заполненного Model
            
            # Filter by listing type
            filter_idx = 0
            if sold_only:
                # Для проданных товаров используем CompletedItems API
                return self._search_completed_items(search_term, category_id, limit)
            else:
                params[f'itemFilter({filter_idx}).name'] = 'ListingType'
                params[f'itemFilter({filter_idx}).value'] = 'FixedPrice'
                filter_idx += 1
            
            # Filter by condition - ищем и новые и б/у
            params[f'itemFilter({filter_idx}).name'] = 'Condition'
            params[f'itemFilter({filter_idx}).value(0)'] = 'New'
            params[f'itemFilter({filter_idx}).value(1)'] = 'Used'
            
            print(f"[EbayClient] Searching eBay Finding API (keywords only, no UPC/EAN filters) for: {search_term}")
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                # Check for API errors in response (eBay returns 200 OK even with auth errors)
                if 'errorMessage' in data:
                    error_msg = str(data.get('errorMessage', {}))
                    print(f"[EbayClient] eBay API returned error: {error_msg}. Falling back to scraping...")
                    try:
                        comps = self._scrape_ebay_search(search_term, limit)
                        if comps:
                            return comps
                    except Exception as e:
                        print(f"[EbayClient] Scraping fallback error: {e}")
                    return []
                
                response = data.get('findItemsAdvancedResponse', [{}])[0]
                search_result = response.get('searchResult', [{}])[0]
                items = search_result.get('item', [])
                
                if not items:
                    print(f"[EbayClient] No items found for: {search_term} (Finding API). Trying HTML scrape fallback...")
                    try:
                        comps_html = self._scrape_ebay_search(search_term, limit)
                        if comps_html:
                            return comps_html
                    except Exception as e:
                        print(f"[EbayClient] HTML scrape fallback error: {e}")
                    return []
                
                comps = []
                for item in items[:limit]:
                    try:
                        # Extract item ID
                        item_id = item.get('itemId', [''])[0]
                        
                        # Extract title
                        item_title = item.get('title', [''])[0]
                        
                        # Extract price
                        price_elem = item.get('sellingStatus', [{}])[0].get('currentPrice', [{}])[0]
                        price = float(price_elem.get('__value__', 0))
                        currency = price_elem.get('@currencyId', 'USD')
                        
                        # Extract shipping cost
                        shipping_info = item.get('shippingInfo', [{}])[0]
                        shipping_cost = 0
                        if shipping_info:
                            shipping_cost_elem = shipping_info.get('shippingServiceCost', [{}])[0]
                            if shipping_cost_elem:
                                shipping_cost = float(shipping_cost_elem.get('__value__', 0))
                        
                        # Extract condition
                        condition_elem = item.get('condition', [{}])[0]
                        condition_id = condition_elem.get('conditionId', [''])[0] if condition_elem else ''
                        condition_text = condition_elem.get('conditionDisplayName', [''])[0] if condition_elem else 'Used'
                        
                        # Extract image
                        gallery_url = item.get('galleryURL', [''])[0]
                        
                        # Extract view item URL
                        view_item_url = item.get('viewItemURL', [''])[0]
                        
                        # Extract location
                        location = item.get('location', '')
                        
                        # Extract seller info
                        seller_info = item.get('sellerInfo', [{}])[0]
                        seller_rating = 0
                        if seller_info:
                            seller_rating = int(seller_info.get('feedbackScore', [0])[0])
                        
                        # Map condition
                        condition = self._map_condition_from_id(condition_id) or self._map_condition_from_text(condition_text)
                        
                        comps.append({
                            'item_id': item_id,
                            'title': item_title,
                            'price': price,
                            'currency': currency,
                            'condition': condition,
                            'condition_text': condition_text,
                            'shipping_cost': shipping_cost,
                            'total_price': price + shipping_cost,
                            'seller_rating': seller_rating,
                            'location': location,
                            'url': view_item_url,
                            'image_url': gallery_url,
                            'sold_date': None,  # Finding API doesn't provide sold date
                            'note': 'eBay Finding API',
                        })
                    except (ValueError, KeyError, IndexError) as e:
                        print(f"[EbayClient] Error parsing item: {e}")
                        continue
                
                print(f"[EbayClient] Found {len(comps)} comparable items")
                return comps
            else:
                error_text = resp.text[:500]
                print(f"[EbayClient] eBay Finding API error {resp.status_code}: {error_text}")
                # Fallback to scraping
                try:
                    comps = self._scrape_ebay_search(search_term, limit)
                    if comps:
                        return comps
                except Exception as e:
                    print(f"[EbayClient] Scraping fallback error: {e}")
        except Exception as e:
            print(f"[EbayClient] Error in search_comps: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to scraping
            try:
                comps = self._scrape_ebay_search(search_term, limit)
                if comps:
                    return comps
            except:
                pass
        
        return []
    
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
        
        def _fetch(params) -> List[Dict[str, Any]]:
            url = 'https://www.ebay.com/sch/i.html'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.ebay.com/',
            }
            try:
                response = requests.get(url, params=params, headers=headers, timeout=8)
                if not response.ok:
                    return []
                from bs4 import BeautifulSoup  # local import for safety
                soup = BeautifulSoup(response.content, 'html.parser')
                items = soup.find_all('li', {'class': 's-item'})[:limit]
                out = []
                for item in items:
                    try:
                        title_elem = item.find('div', {'class': 's-item__title'})
                        title = title_elem.get_text(strip=True) if title_elem else ''
                        if not title or 'Shop on eBay' in title:
                            continue
                        price_elem = item.find('span', {'class': 's-item__price'})
                        price_text = price_elem.get_text(strip=True) if price_elem else ''
                        price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                        price = float(price_match.group(1).replace(',', '')) if price_match else 0
                        if price == 0:
                            continue
                        link_elem = item.find('a', {'class': 's-item__link'})
                        item_url = link_elem.get('href', '') if link_elem else ''
                        item_id_match = re.search(r'/itm/(\\d+)', item_url)
                        item_id = item_id_match.group(1) if item_id_match else ''
                        img_elem = item.find('img', {'class': re.compile('s-item__image-img')})
                        image_url = img_elem.get('src', '') if img_elem else ''
                        shipping_elem = item.find('span', {'class': 's-item__shipping'})
                        shipping_text = shipping_elem.get_text(strip=True) if shipping_elem else ''
                        shipping_cost = 0 if 'Free' in shipping_text else 0.0
                        condition_elem = item.find('span', {'class': 'SECONDARY_INFO'})
                        condition_text = condition_elem.get_text(strip=True) if condition_elem else ''
                        condition = self._map_condition_from_text(condition_text)
                        out.append({
                            'item_id': item_id,
                            'title': title[:120],
                            'price': price,
                            'condition': condition,
                            'shipping_cost': shipping_cost,
                            'seller_rating': 0,
                            'location': '',
                            'url': item_url,
                            'image_url': image_url,
                            'sold_date': None,
                            'note': 'eBay web search',
                        })
                    except Exception as e:
                        print(f"Error parsing item: {e}")
                        continue
                return out
            except Exception as e:
                print(f"eBay scraping failed: {e}")
                return []

        # 1) Попробуем проданные (реальный рынок)
        params_sold = {
            '_nkw': query,
            '_sacat': '0',
            'LH_Sold': '1',
            'LH_Complete': '1',
            '_sop': '13',  # Recently sold
            'rt': 'nc',
        }
        comps = _fetch(params_sold)
        if comps:
            return comps
        # 2) Если пусто — попробуем активные листинги (чаще не блокируются)
        params_active = {
            '_nkw': query,
            '_sacat': '0',
            '_sop': '12',  # Price + shipping lowest
            'rt': 'nc',
        }
        return _fetch(params_active)
    
    def _search_completed_items(self, query: str, category_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for completed/sold items using eBay Finding API.
        Это дает более точные цены, так как показывает реально проданные товары.
        """
        import os
        
        ebay_app_id = os.getenv('EBAY_APP_ID') or getattr(settings, 'EBAY_APP_ID', '')
        if not ebay_app_id:
            return []
        
        try:
            url = 'https://svcs.ebay.com/services/search/FindingService/v1'
            params = {
                'OPERATION-NAME': 'findCompletedItems',
                'SERVICE-VERSION': '1.0.0',
                'SECURITY-APPNAME': ebay_app_id,
                'RESPONSE-DATA-FORMAT': 'JSON',
                'REST-PAYLOAD': '',
                'keywords': query,
                'paginationInput.entriesPerPage': str(min(limit, 100)),
                'sortOrder': 'PricePlusShippingLowest',
            }
            
            if category_id:
                params['categoryId'] = category_id
            
            print(f"[EbayClient] Searching completed items for: {query}")
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                response = data.get('findCompletedItemsResponse', [{}])[0]
                search_result = response.get('searchResult', [{}])[0]
                items = search_result.get('item', [])
                
                if not items:
                    print(f"[EbayClient] No completed items found for: {query}")
                    return []
                
                comps = []
                for item in items[:limit]:
                    try:
                        item_id = item.get('itemId', [''])[0]
                        item_title = item.get('title', [''])[0]
                        
                        # Для проданных товаров берем sold price
                        selling_status = item.get('sellingStatus', [{}])[0]
                        price_elem = selling_status.get('currentPrice', [{}])[0]
                        price = float(price_elem.get('__value__', 0))
                        currency = price_elem.get('@currencyId', 'USD')
                        
                        # Дата продажи
                        sold_date_str = selling_status.get('soldDate', [''])[0]
                        
                        shipping_info = item.get('shippingInfo', [{}])[0]
                        shipping_cost = 0
                        if shipping_info:
                            shipping_cost_elem = shipping_info.get('shippingServiceCost', [{}])[0]
                            if shipping_cost_elem:
                                shipping_cost = float(shipping_cost_elem.get('__value__', 0))
                        
                        condition_elem = item.get('condition', [{}])[0]
                        condition_id = condition_elem.get('conditionId', [''])[0] if condition_elem else ''
                        condition_text = condition_elem.get('conditionDisplayName', [''])[0] if condition_elem else 'Used'
                        
                        gallery_url = item.get('galleryURL', [''])[0]
                        view_item_url = item.get('viewItemURL', [''])[0]
                        location = item.get('location', '')
                        
                        seller_info = item.get('sellerInfo', [{}])[0]
                        seller_rating = 0
                        if seller_info:
                            seller_rating = int(seller_info.get('feedbackScore', [0])[0])
                        
                        condition = self._map_condition_from_id(condition_id) or self._map_condition_from_text(condition_text)
                        
                        comps.append({
                            'item_id': item_id,
                            'title': item_title,
                            'price': price,
                            'currency': currency,
                            'condition': condition,
                            'condition_text': condition_text,
                            'shipping_cost': shipping_cost,
                            'total_price': price + shipping_cost,
                            'seller_rating': seller_rating,
                            'location': location,
                            'url': view_item_url,
                            'image_url': gallery_url,
                            'sold_date': sold_date_str,
                            'note': 'eBay Completed Items (sold)',
                        })
                    except (ValueError, KeyError, IndexError) as e:
                        print(f"[EbayClient] Error parsing completed item: {e}")
                        continue
                
                print(f"[EbayClient] Found {len(comps)} completed items")
                return comps
            else:
                error_text = resp.text[:500]
                print(f"[EbayClient] Completed items API error {resp.status_code}: {error_text}")
        except Exception as e:
            print(f"[EbayClient] Error searching completed items: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def _map_condition_from_id(self, condition_id: str) -> Optional[str]:
        """Map eBay condition ID to enum."""
        condition_map = {
            '1000': 'NEW',
            '1500': 'NEW_OTHER',
            '2000': 'USED_GOOD',
            '2500': 'USED_VERY_GOOD',
            '3000': 'USED_EXCELLENT',
            '4000': 'USED_ACCEPTABLE',
            '5000': 'FOR_PARTS_OR_NOT_WORKING',
        }
        return condition_map.get(condition_id)
    
    def _map_condition_from_text(self, text: str) -> str:
        """Map eBay condition text to enum."""
        text_lower = text.lower()
        if 'new' in text_lower and 'other' not in text_lower:
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
