"""
Management command to sync eBay sales and update inventory.

Usage:
    python manage.py sync_ebay_sales
    python manage.py sync_ebay_sales --since 2025-01-01
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import json

from apps.marketplaces.ebay.models import EbayCandidate
from apps.marketplaces.ebay.services.client import EbayClient


class Command(BaseCommand):
    help = 'Sync eBay sales and update inventory quantities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            type=str,
            help='Sync orders since date (YYYY-MM-DD). Default: last 7 days',
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Dry run - do not update inventory',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Parse since date
        since_str = options.get('since')
        if since_str:
            try:
                since = datetime.strptime(since_str, '%Y-%m-%d')
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid date format: {since_str}. Use YYYY-MM-DD'))
                return
        else:
            # Default: last 7 days
            since = timezone.now() - timedelta(days=7)

        dry_run = options.get('dry_run', False)

        self.stdout.write(f'Syncing eBay sales since {since.strftime("%Y-%m-%d")}...')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Fetch orders from eBay
        client = EbayClient()

        try:
            orders = client.fetch_orders(since=since)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to fetch orders: {str(e)}'))
            return

        if not orders:
            self.stdout.write(self.style.SUCCESS('No new orders found.'))
            return

        self.stdout.write(f'Found {len(orders)} order(s)')

        # Process each order
        processed = 0
        errors = 0

        for order in orders:
            order_id = order.get('order_id')
            item_id = order.get('item_id')
            quantity_sold = order.get('quantity', 1)

            self.stdout.write(f'Processing order {order_id} - Item {item_id} (qty: {quantity_sold})')

            # Find candidate by eBay item ID
            try:
                candidate = EbayCandidate.objects.get(ebay_item_id=item_id)
            except EbayCandidate.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  No candidate found for item {item_id}'))
                errors += 1
                continue

            batch = candidate.photo_batch

            # Check if batch has locations data
            if not hasattr(batch, 'locations') or not batch.locations:
                self.stdout.write(self.style.WARNING(f'  Batch has no locations data'))
                errors += 1
                continue

            # Decrease quantity
            total_qty = sum(loc.get('qty', 0) for loc in batch.locations)

            if total_qty < quantity_sold:
                self.stdout.write(self.style.WARNING(
                    f'  Insufficient quantity! Available: {total_qty}, Sold: {quantity_sold}'
                ))
                errors += 1
                continue

            if not dry_run:
                # Decrease from first available location
                remaining = quantity_sold

                for location in batch.locations:
                    if remaining <= 0:
                        break

                    loc_qty = location.get('qty', 0)

                    if loc_qty > 0:
                        deduct = min(loc_qty, remaining)
                        location['qty'] = loc_qty - deduct
                        remaining -= deduct

                        self.stdout.write(f'  Decreased {deduct} from location "{location.get("name")}"')

                # Save batch
                batch.save()

                # Add log to candidate
                candidate.add_log(
                    'info',
                    f'Sale synced: Order {order_id}, qty {quantity_sold}',
                    {'order_id': order_id, 'quantity': quantity_sold}
                )

                # Check if out of stock
                new_total = sum(loc.get('qty', 0) for loc in batch.locations)
                if new_total == 0:
                    self.stdout.write(self.style.WARNING(f'  Item is now OUT OF STOCK'))

                    # Optionally end listing
                    # candidate.status = 'ended'
                    # candidate.save()

            processed += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Processed: {processed}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'⚠ Errors: {errors}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were saved'))
