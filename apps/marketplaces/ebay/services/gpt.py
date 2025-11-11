"""
GPT/AI services for eBay listing generation (stub implementation).

This module provides AI-powered services for:
- Vision extraction (OCR, brand/model detection)
- Listing content generation (title, description, bullets)
- Comps selection and analysis

For MVP, these are stubs that return mock data.
In production, replace with actual GPT-4 Vision and GPT-4 API calls.
"""
import time
from typing import List, Dict, Any, Optional
from django.conf import settings


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
        Extract product information from images using GPT-4 Vision (STUB).

        Analyzes product photos to extract:
        - Brand
        - Model/line
        - Variant (color, size, etc.)
        - Volume/size
        - Condition (visual assessment)
        - Product codes (UPC, EAN, ISBN, etc.)
        - Key terms and features

        Args:
            image_urls: List of product image URLs

        Returns:
            Extracted data dict

        Prompt for GPT-4 Vision:
        ```
        Analyze these product photos (labels, barcodes, boxes).
        Extract:
        - Brand
        - Model/line
        - Variant (color, flavor, etc.)
        - Volume/size
        - Condition (visual assessment)
        - Product codes (UPC, EAN, ISBN visible on labels)
        - Key product terms

        If uncertain, return UNKNOWN.
        Return JSON: {
            brand, model, variant, volume, condition_guess,
            codes: [{type, value}],
            key_terms: []
        }
        Do not make up information.
        ```

        In production, this would call OpenAI GPT-4 Vision API.
        """
        time.sleep(0.5)  # Simulate API delay

        # Mock extraction based on simple heuristics
        # In production, this would use actual vision analysis

        return {
            'brand': 'UNKNOWN',
            'model': 'UNKNOWN',
            'variant': '',
            'volume': '',
            'condition_guess': 'USED_GOOD',
            'codes': [
                # Mock codes - in production these would be extracted via OCR
                # {'type': 'UPC', 'value': '012345678905'},
            ],
            'key_terms': [
                'authentic',
                'original',
            ],
            'confidence': 0.7,  # Overall confidence score
            'notes': 'STUB: Replace with GPT-4 Vision in production',
        }

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

        In production, this would call OpenAI GPT-4 API.
        """
        time.sleep(0.3)

        # Extract some basic info
        brand = extracted_data.get('brand', 'Generic')
        model = extracted_data.get('model', 'Product')
        condition = extracted_data.get('condition_guess', 'USED_GOOD')

        # Generate mock listing
        title = f"{brand} {model}".strip()
        if len(title) > 75:
            title = title[:75]

        # Map condition
        condition_map = {
            'NEW': 'NEW',
            'USED_EXCELLENT': 'USED_EXCELLENT',
            'USED_GOOD': 'USED_GOOD',
            'USED_ACCEPTABLE': 'USED_ACCEPTABLE',
        }
        ebay_condition = condition_map.get(condition, 'USED_GOOD')

        return {
            'title': title,
            'condition': ebay_condition,
            'specifics': {
                'Brand': brand if brand != 'UNKNOWN' else 'REQUIRED_MISSING',
                'Condition': ebay_condition,
            },
            'bullets': [
                'Authentic product',
                f'Condition: {ebay_condition.replace("_", " ").title()}',
                'Fast shipping',
                'Carefully packaged',
                'Buy with confidence',
            ],
            'description_md': f"""# {title}

This is an authentic {brand} {model} in {ebay_condition.replace('_', ' ').lower()} condition.

## Condition Details

Item has been carefully inspected and is ready for a new home. See photos for exact condition.

## Shipping

Fast and secure shipping. Item will be carefully packaged to ensure safe delivery.

**Note:** STUB description - replace with GPT-4 generated content in production.
""",
            'notes': 'STUB: Replace with GPT-4 in production',
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
