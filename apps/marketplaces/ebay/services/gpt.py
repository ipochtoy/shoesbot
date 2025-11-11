"""
GPT/AI services for eBay listing generation.

This module provides AI-powered services for:
- Vision extraction (OCR, brand/model detection)
- Listing content generation (title, description, bullets)
- Comps selection and analysis

Uses existing AI helpers from photos app.
"""
import time
import sys
import os
from typing import List, Dict, Any, Optional
from django.conf import settings

# Import existing AI helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../shoessite/photos'))
try:
    from photos.ai_helpers import auto_fill_product_card, analyze_photos_with_vision
except ImportError:
    auto_fill_product_card = None
    analyze_photos_with_vision = None


class GPTService:
    """
    GPT-based AI service for listing generation.

    Stub implementation for MVP.
    """

    def __init__(self):
        """Initialize GPT service."""
        self.provider = getattr(settings, 'GPT_PROVIDER', 'openai')

    def vision_extract(self, image_urls: List[str]) -> Dict[str, Any]:
        """
        Extract product information from images using GPT-4 Vision.

        Uses existing analyze_photos_with_vision from photos app.

        Args:
            image_urls: List of product image URLs

        Returns:
            Extracted data dict
        """
        if not image_urls:
            return {
                'brand': 'UNKNOWN',
                'model': 'UNKNOWN',
                'variant': '',
                'volume': '',
                'condition_guess': 'USED_GOOD',
                'codes': [],
                'key_terms': [],
                'confidence': 0.0,
                'notes': 'No images provided',
            }

        # Use existing vision helper if available
        if analyze_photos_with_vision:
            try:
                vision_result = analyze_photos_with_vision(image_urls)
                
                # Map vision result to eBay format
                return {
                    'brand': vision_result.get('brand', 'UNKNOWN'),
                    'model': vision_result.get('model', 'UNKNOWN'),
                    'variant': vision_result.get('color', ''),
                    'volume': vision_result.get('size', ''),
                    'condition_guess': self._map_condition_to_ebay(vision_result.get('condition', '')),
                    'codes': self._extract_codes_from_vision(vision_result),
                    'key_terms': vision_result.get('features', []),
                    'confidence': 0.8,
                    'notes': 'Extracted via GPT-4 Vision',
                }
            except Exception as e:
                print(f"Vision extraction error: {e}")
        
        # Fallback to stub
        return {
            'brand': 'UNKNOWN',
            'model': 'UNKNOWN',
            'variant': '',
            'volume': '',
            'condition_guess': 'USED_GOOD',
            'codes': [],
            'key_terms': [],
            'confidence': 0.0,
            'notes': f'Vision API not available: {str(e) if "e" in locals() else "No helper found"}',
        }
    
    def _map_condition_to_ebay(self, condition_str: str) -> str:
        """Map Russian condition to eBay condition enum."""
        condition_map = {
            'новое': 'NEW',
            'new': 'NEW',
            'б/у': 'USED_GOOD',
            'used': 'USED_GOOD',
            'отличное': 'USED_EXCELLENT',
            'excellent': 'USED_EXCELLENT',
            'хорошее': 'USED_VERY_GOOD',
            'very good': 'USED_VERY_GOOD',
        }
        condition_lower = condition_str.lower() if condition_str else ''
        return condition_map.get(condition_lower, 'USED_GOOD')
    
    def _extract_codes_from_vision(self, vision_result: Dict) -> List[Dict]:
        """Extract product codes from vision result."""
        codes = []
        
        # Look for UPC/EAN/ISBN in vision result
        if 'upc' in vision_result and vision_result['upc']:
            codes.append({'type': 'UPC', 'value': vision_result['upc']})
        if 'ean' in vision_result and vision_result['ean']:
            codes.append({'type': 'EAN', 'value': vision_result['ean']})
        if 'isbn' in vision_result and vision_result['isbn']:
            codes.append({'type': 'ISBN', 'value': vision_result['isbn']})
        
        return codes

    def write_listing(
        self,
        extracted_data: Dict[str, Any],
        category_name: str = '',
        language: str = 'EN'
    ) -> Dict[str, Any]:
        """
        Generate eBay listing content using GPT-4 (STUB).

        Creates:
        - Title (max 80 chars): Brand + Model + Size/Volume + Condition
        - Description (2-3 paragraphs)
        - Bullet points (5 key features)
        - Item specifics

        Args:
            extracted_data: Data from vision_extract
            category_name: eBay category name
            language: Listing language

        Returns:
            Generated listing content

        Prompt for GPT-4:
        ```
        Generate eBay listing for this product.
        Input data: {extracted_data}
        Category: {category_name}

        Requirements:
        - Title: ≤80 chars, format: Brand + Model + Size/Volume + Condition
        - Description: 2-3 paragraphs, professional tone
        - Bullets: 5 key features
        - No guarantees, no health/medical claims
        - Highlight condition and authenticity

        Return JSON: {
            title,
            condition,
            specifics: {...},
            bullets: [...],
            description_md
        }

        If required specific is missing data, mark as REQUIRED_MISSING.
        ```

        """
        # Extract basic info
        brand = extracted_data.get('brand', 'Generic')
        model = extracted_data.get('model', 'Product')
        variant = extracted_data.get('variant', '')
        volume = extracted_data.get('volume', '')
        condition = extracted_data.get('condition_guess', 'USED_GOOD')
        
        # Try to use OpenAI API if available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and brand != 'UNKNOWN':
            try:
                import requests
                
                prompt = f"""Generate eBay listing for this product:

Brand: {brand}
Model: {model}
Variant: {variant}
Size/Volume: {volume}
Condition: {condition}
Category: {category_name}

Requirements:
- Title: MAX 80 characters, format: Brand + Model + Size/Volume + Condition
- Description: 2-3 paragraphs in markdown, professional, no guarantees/health claims
- Bullets: 5 key features
- Item specifics: Brand, Condition, and other relevant attributes

Return ONLY valid JSON:
{{
  "title": "string (max 80 chars)",
  "condition": "eBay condition enum",
  "specifics": {{"Brand": "...", ...}},
  "bullets": ["...", "...", "...", "...", "..."],
  "description_md": "markdown text"
}}"""

                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': 'gpt-4o',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.3,
                        'max_tokens': 800,
                    },
                    timeout=30
                )
                
                if response.ok:
                    result = response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    # Parse JSON from response
                    import json
                    # Remove markdown code blocks if present
                    content = content.strip()
                    if content.startswith('```'):
                        content = content.split('\n', 1)[1]
                        content = content.rsplit('```', 1)[0]
                    content = content.strip()
                    
                    listing_data = json.loads(content)
                    
                    # Ensure title is ≤80 chars
                    if len(listing_data.get('title', '')) > 80:
                        listing_data['title'] = listing_data['title'][:77] + '...'
                    
                    listing_data['notes'] = 'Generated by GPT-4'
                    return listing_data
                    
            except Exception as e:
                print(f"GPT listing generation error: {e}")
                # Fall through to stub
        
        # Fallback: simple title generation
        title_parts = [brand, model, variant, volume]
        title = ' '.join([p for p in title_parts if p and p != 'UNKNOWN'])
        if len(title) > 75:
            title = title[:75]
        if len(title) < 80 and condition:
            condition_display = condition.replace('_', ' ').title()
            remaining = 80 - len(title) - 3
            if len(condition_display) <= remaining:
                title = f"{title} - {condition_display}"
        
        return {
            'title': title[:80],
            'condition': condition,
            'specifics': {
                'Brand': brand if brand != 'UNKNOWN' else 'REQUIRED_MISSING',
                'Condition': condition,
            },
            'bullets': [
                'Authentic product',
                f'Condition: {condition.replace("_", " ").title()}',
                'Fast shipping with tracking',
                'Carefully packaged',
                'Buy with confidence',
            ],
            'description_md': f"""# {title}

Authentic {brand} {model} in {condition.replace('_', ' ').lower()} condition.

## Condition
Item has been inspected. See photos for exact condition and details.

## Shipping
Fast and secure shipping. Item will be carefully packaged.
""",
            'notes': 'Fallback listing (GPT API not available or insufficient data)',
        }

    def select_comps(self, comps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select best comparable items and calculate statistics (STUB).

        Filters comps based on:
        - Condition match
        - Seller rating (prefer high-rated sellers)
        - Location (prefer domestic)
        - Shipping cost (prefer free shipping or low cost)

        Args:
            comps: List of comparable items from eBay search

        Returns:
            Analysis with selected comps and pricing stats

        Prompt for GPT-4:
        ```
        Analyze these eBay comparable listings.
        Select the most relevant comps based on:
        - Similar condition
        - High seller ratings (>95%)
        - Domestic shipping
        - Free or low shipping cost

        Calculate pricing statistics (median, p25, p75).

        Return JSON: {
            selected_ids: [...],
            median,
            p25,
            p75,
            rationale
        }
        ```

        In production, this could use GPT-4 for intelligent filtering.
        For now, use simple heuristics.
        """
        if not comps:
            return {
                'selected': [],
                'median': 0,
                'p25': 0,
                'p75': 0,
                'count': 0,
            }

        # Simple filtering: prefer free shipping and high ratings
        filtered = [
            comp for comp in comps
            if comp.get('seller_rating', 0) >= 95
            and comp.get('shipping_cost', 0) <= 7.99
        ]

        # If too few after filtering, use all comps
        if len(filtered) < 5:
            filtered = comps

        # Extract prices
        prices = sorted([comp['price'] for comp in filtered])

        if not prices:
            return {
                'selected': [],
                'median': 0,
                'p25': 0,
                'p75': 0,
                'count': 0,
            }

        # Calculate percentiles
        def percentile(data, p):
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] * (1 - c) + data[f + 1] * c
            return data[f]

        median = percentile(prices, 0.5)
        p25 = percentile(prices, 0.25)
        p75 = percentile(prices, 0.75)

        return {
            'selected': [comp['item_id'] for comp in filtered],
            'selected_comps': filtered,
            'median': round(median, 2),
            'p25': round(p25, 2),
            'p75': round(p75, 2),
            'count': len(filtered),
            'notes': 'Simple heuristic filtering - replace with GPT-4 in production',
        }

    def calculate_final_price(
        self,
        median: float,
        below_median_pct: float = None,
        ship_cost: float = None
    ) -> Dict[str, Any]:
        """
        Calculate final listing price.

        Formula:
        - Target = median * (1 - X%)
        - Final = target + ship_cost (for free shipping)

        Args:
            median: Market median price
            below_median_pct: Percentage below median (e.g., 0.08 for 8%)
            ship_cost: Shipping cost to include

        Returns:
            Pricing calculation

        """
        if below_median_pct is None:
            below_median_pct = getattr(settings, 'PRICE_BELOW_MEDIAN_PCT', 0.08)

        if ship_cost is None:
            ship_cost = getattr(settings, 'DEFAULT_SHIP_COST', 4.99)

        # Calculate target price (below median)
        target = median * (1 - below_median_pct)

        # Round down to nearest cent
        target = round(target, 2)

        # Add shipping for free shipping listings
        final = target + ship_cost
        final = round(final, 2)

        return {
            'price_suggested': target,
            'price_final': final,
            'median': median,
            'below_median_pct': below_median_pct,
            'ship_cost': ship_cost,
            'rationale': f'Set {below_median_pct*100}% below median (${median:.2f}) = ${target:.2f}, plus ${ship_cost:.2f} shipping = ${final:.2f}',
        }
