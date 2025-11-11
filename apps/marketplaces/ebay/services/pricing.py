"""
Pricing service for eBay listings.

Handles:
- Fetching comparable listings
- Analyzing market prices
- Calculating suggested prices
"""
from typing import Dict, Any, Optional
from django.conf import settings
from .client import EbayClient
from .gpt import GPTService


class PricingService:
    """
    Service for pricing analysis and suggestions.
    """

    def __init__(self):
        """Initialize pricing service."""
        self.ebay_client = EbayClient()
        self.gpt_service = GPTService()

    def get_comps(
        self,
        q: Optional[str] = None,
        upc: Optional[str] = None,
        ean: Optional[str] = None,
        isbn: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comparable listings and pricing analysis.

        Args:
            q: Search query
            upc: UPC code
            ean: EAN code
            isbn: ISBN code
            category_id: eBay category ID

        Returns:
            Dict with comps, statistics, and pricing suggestion
        """
        # Search for comparable items on eBay
        comps = self.ebay_client.search_comps(
            query=q,
            upc=upc,
            ean=ean,
            isbn=isbn,
            category_id=category_id,
            limit=20
        )

        if not comps:
            return {
                'comps': [],
                'median': 0,
                'p25': 0,
                'p75': 0,
                'count': 0,
                'price_suggested': 0,
                'price_final': 0,
                'message': 'No comparable items found'
            }

        # Use GPT service to select best comps and calculate stats
        analysis = self.gpt_service.select_comps(comps)

        # Calculate final pricing
        if analysis['median'] > 0:
            pricing = self.gpt_service.calculate_final_price(
                median=analysis['median']
            )

            return {
                'comps': analysis.get('selected_comps', comps)[:10],  # Return top 10
                'median': analysis['median'],
                'p25': analysis['p25'],
                'p75': analysis['p75'],
                'count': analysis['count'],
                'price_suggested': pricing['price_suggested'],
                'price_final': pricing['price_final'],
                'rationale': pricing.get('rationale', ''),
            }

        return {
            'comps': comps[:10],
            'median': 0,
            'p25': 0,
            'p75': 0,
            'count': len(comps),
            'price_suggested': 0,
            'price_final': 0,
            'message': 'Could not calculate pricing statistics'
        }

    def calculate_price_for_candidate(self, candidate) -> Dict[str, Any]:
        """
        Calculate pricing for a specific candidate.

        Uses product data from PhotoBatch to search for comps.

        Args:
            candidate: EbayCandidate instance

        Returns:
            Pricing analysis dict
        """
        batch = candidate.photo_batch

        # Build search query from batch data
        search_parts = []

        if batch.brand:
            search_parts.append(batch.brand)
        if batch.title:
            search_parts.append(batch.title)

        search_query = ' '.join(search_parts).strip()

        # Try to get UPC/EAN from barcodes
        upc = None
        ean = None

        # Get first barcode from photos
        first_photo = batch.photos.first()
        if first_photo:
            first_barcode = first_photo.barcodes.filter(symbology__in=['EAN13', 'UPCA', 'UPCE']).first()
            if first_barcode:
                if 'UPC' in first_barcode.symbology:
                    upc = first_barcode.data
                elif 'EAN' in first_barcode.symbology:
                    ean = first_barcode.data

        # Get comps
        result = self.get_comps(
            q=search_query or 'generic product',
            upc=upc,
            ean=ean,
            category_id=candidate.category_id or None,
        )

        # Store comps in candidate
        if result.get('comps'):
            candidate.comps = result['comps']

        # Update pricing
        if result.get('price_suggested'):
            candidate.price_suggested = result['price_suggested']
            candidate.price_final = result['price_final']

        return result

    def reprice_candidate(self, candidate) -> Dict[str, Any]:
        """
        Recalculate price for a candidate based on current market.

        Args:
            candidate: EbayCandidate instance

        Returns:
            Reprice result dict
        """
        old_price = candidate.price_final

        # Get fresh comps and pricing
        result = self.calculate_price_for_candidate(candidate)

        new_price = result.get('price_final', old_price)

        # Update if price changed
        if new_price and new_price != old_price:
            candidate.price_final = new_price
            candidate.price_suggested = result.get('price_suggested')
            candidate.comps = result.get('comps', [])

            # If already listed, update on eBay
            if candidate.status == 'listed' and candidate.ebay_item_id:
                try:
                    self.ebay_client.update_price(
                        candidate.ebay_item_id,
                        float(new_price)
                    )
                    candidate.add_log(
                        'info',
                        f'Price updated on eBay: ${old_price} → ${new_price}',
                        {'old_price': str(old_price), 'new_price': str(new_price)}
                    )
                except Exception as e:
                    candidate.add_log('error', f'Failed to update price on eBay: {str(e)}')
                    return {
                        'success': False,
                        'message': f'Failed to update price on eBay: {str(e)}',
                        'old_price': old_price,
                        'new_price': new_price,
                    }

            candidate.save()

            return {
                'success': True,
                'message': f'Price updated: ${old_price} → ${new_price}',
                'old_price': old_price,
                'new_price': new_price,
                'median': result.get('median'),
            }

        return {
            'success': True,
            'message': 'Price unchanged',
            'old_price': old_price,
            'new_price': new_price,
        }
