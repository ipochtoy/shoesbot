"""
Tests for eBay marketplace pipeline.
"""
from django.test import TestCase
from django.utils import timezone

import sys
import os

# Add shoessite to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shoessite'))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoessite.settings')

import django
django.setup()

from photos.models import PhotoBatch
from apps.marketplaces.ebay.models import EbayCandidate
from apps.marketplaces.ebay.services.pipeline import prepare_candidate, publish_candidate


class EbayPipelineTestCase(TestCase):
    """Test eBay preparation and publishing pipeline."""

    def setUp(self):
        """Create test data."""
        # Create PhotoBatch
        self.batch = PhotoBatch.objects.create(
            correlation_id='test123',
            chat_id=123456,
            title='Test Product - Nike Shoes',
            brand='Nike',
            category='Shoes',
            price=99.99,
        )

    def test_create_candidate(self):
        """Test creating an eBay candidate."""
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='draft',
        )

        self.assertEqual(candidate.status, 'draft')
        self.assertEqual(candidate.photo_batch, self.batch)
        self.assertIsNotNone(candidate.created_at)

    def test_prepare_candidate(self):
        """Test preparation pipeline."""
        # Create candidate
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='draft',
        )

        # Run prepare
        result = prepare_candidate(candidate.id)

        # Check result
        self.assertTrue(result.get('success'))
        self.assertIn(result.get('status'), ['draft', 'ready'])

        # Refresh candidate
        candidate.refresh_from_db()

        # Check logs
        self.assertTrue(len(candidate.logs) > 0)
        self.assertIsNotNone(candidate.prepared_at)

        # Check generated fields
        self.assertIsNotNone(candidate.title)
        self.assertIsNotNone(candidate.category_id)

        # Check pricing
        if candidate.price_suggested:
            self.assertGreater(candidate.price_suggested, 0)

    def test_publish_candidate_without_required_fields(self):
        """Test that publishing fails without required fields."""
        # Create candidate without required fields
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='draft',
        )

        # Try to publish
        result = publish_candidate(candidate.id)

        # Should fail
        self.assertFalse(result.get('success'))
        self.assertIn('missing', result.get('message', '').lower())

    def test_publish_candidate_success(self):
        """Test successful publishing with all required fields."""
        # Create candidate with all required fields
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='ready',
            title='Nike Shoes Test Product',
            category_id='12345',
            condition='USED_GOOD',
            price_final=49.99,
            photos=['https://example.com/photo1.jpg'],
        )

        # Publish
        result = publish_candidate(candidate.id)

        # Should succeed
        self.assertTrue(result.get('success'))

        # Refresh candidate
        candidate.refresh_from_db()

        # Check status
        self.assertEqual(candidate.status, 'listed')
        self.assertIsNotNone(candidate.listed_at)
        self.assertIsNotNone(candidate.ebay_item_id)

    def test_missing_required_fields_property(self):
        """Test missing_required_fields property."""
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='draft',
        )

        missing = candidate.missing_required_fields

        # Should have missing fields
        self.assertIn('title', missing)
        self.assertIn('category_id', missing)
        self.assertIn('condition', missing)
        self.assertIn('price_final', missing)
        self.assertIn('photos', missing)

        # Fill in fields
        candidate.title = 'Test'
        candidate.category_id = '12345'
        candidate.condition = 'NEW'
        candidate.price_final = 99.99
        candidate.photos = ['https://example.com/photo.jpg']
        candidate.save()

        # Check again
        missing = candidate.missing_required_fields
        self.assertEqual(len(missing), 0)

    def test_add_log(self):
        """Test adding log entries."""
        candidate = EbayCandidate.objects.create(
            photo_batch=self.batch,
            status='draft',
        )

        # Add log
        candidate.add_log('info', 'Test log entry', {'key': 'value'})

        # Check
        self.assertEqual(len(candidate.logs), 1)
        log = candidate.logs[0]

        self.assertEqual(log['level'], 'info')
        self.assertEqual(log['message'], 'Test log entry')
        self.assertEqual(log['data']['key'], 'value')
        self.assertIn('timestamp', log)


class EbayClientTestCase(TestCase):
    """Test eBay client stub."""

    def test_search_categories(self):
        """Test category search."""
        from apps.marketplaces.ebay.services.client import EbayClient

        client = EbayClient()
        categories = client.search_categories('shoes')

        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)

        # Check first category
        cat = categories[0]
        self.assertIn('category_id', cat)
        self.assertIn('category_name', cat)

    def test_get_required_specifics(self):
        """Test getting required specifics."""
        from apps.marketplaces.ebay.services.client import EbayClient

        client = EbayClient()
        specifics = client.get_required_specifics('12345')

        self.assertIsInstance(specifics, list)
        self.assertGreater(len(specifics), 0)

        # Check first specific
        spec = specifics[0]
        self.assertIn('name', spec)
        self.assertIn('required', spec)

    def test_search_comps(self):
        """Test searching comparable items."""
        from apps.marketplaces.ebay.services.client import EbayClient

        client = EbayClient()
        comps = client.search_comps(query='Nike shoes', limit=10)

        self.assertIsInstance(comps, list)
        self.assertGreater(len(comps), 0)

        # Check first comp
        comp = comps[0]
        self.assertIn('item_id', comp)
        self.assertIn('price', comp)
        self.assertIn('title', comp)


class PricingServiceTestCase(TestCase):
    """Test pricing service."""

    def test_get_comps(self):
        """Test getting comps and pricing."""
        from apps.marketplaces.ebay.services.pricing import PricingService

        service = PricingService()
        result = service.get_comps(q='test product')

        self.assertIn('comps', result)
        self.assertIn('median', result)
        self.assertIn('price_suggested', result)
        self.assertIn('price_final', result)


class GPTServiceTestCase(TestCase):
    """Test GPT service stubs."""

    def test_vision_extract(self):
        """Test vision extraction stub."""
        from apps.marketplaces.ebay.services.gpt import GPTService

        service = GPTService()
        result = service.vision_extract(['https://example.com/photo.jpg'])

        self.assertIn('brand', result)
        self.assertIn('model', result)
        self.assertIn('condition_guess', result)
        self.assertIn('codes', result)
        self.assertIn('key_terms', result)

    def test_write_listing(self):
        """Test listing content generation stub."""
        from apps.marketplaces.ebay.services.gpt import GPTService

        service = GPTService()

        extracted_data = {
            'brand': 'Nike',
            'model': 'Air Max',
            'condition_guess': 'USED_GOOD',
        }

        result = service.write_listing(extracted_data, 'Shoes')

        self.assertIn('title', result)
        self.assertIn('description_md', result)
        self.assertIn('condition', result)
        self.assertIn('specifics', result)
        self.assertIn('bullets', result)

        # Check title length
        self.assertLessEqual(len(result['title']), 80)

    def test_calculate_final_price(self):
        """Test price calculation."""
        from apps.marketplaces.ebay.services.gpt import GPTService

        service = GPTService()
        result = service.calculate_final_price(
            median=100.0,
            below_median_pct=0.08,
            ship_cost=4.99
        )

        self.assertIn('price_suggested', result)
        self.assertIn('price_final', result)

        # Check calculation
        # 100 * (1 - 0.08) = 92
        # 92 + 4.99 = 96.99
        self.assertEqual(result['price_suggested'], 92.0)
        self.assertEqual(result['price_final'], 96.99)


if __name__ == '__main__':
    import unittest
    unittest.main()
