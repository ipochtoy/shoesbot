"""
Django management command to manually add eBay OAuth token.

Usage:
    python manage.py add_ebay_token <access_token> [--sandbox]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.marketplaces.ebay.models import EbayToken


class Command(BaseCommand):
    help = 'Manually add eBay OAuth token to database'

    def add_arguments(self, parser):
        parser.add_argument('access_token', type=str, help='eBay OAuth access token')
        parser.add_argument('--sandbox', action='store_true', help='Use sandbox environment')
        parser.add_argument('--refresh-token', type=str, default='', help='Refresh token (optional)')
        parser.add_argument('--expires-in', type=int, default=7200, help='Token lifetime in seconds (default: 7200)')

    def handle(self, *args, **options):
        access_token = options['access_token']
        sandbox = options['sandbox']
        refresh_token = options['refresh_token']
        expires_in = options['expires_in']
        
        expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        token_obj, created = EbayToken.objects.update_or_create(
            account='default',
            sandbox=sandbox,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created new token (sandbox={sandbox})'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Updated existing token (sandbox={sandbox})'))
        
        self.stdout.write(f'  Expires at: {expires_at}')
        self.stdout.write(f'  Has refresh token: {bool(refresh_token)}')

