"""
eBay marketplace models.
"""
from django.db import models
from django.utils import timezone
from photos.models import PhotoBatch


class EbayCandidate(models.Model):
    """
    eBay listing candidate - represents a product being prepared or listed on eBay.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('listed', 'Listed'),
        ('error', 'Error'),
        ('ended', 'Ended'),
    ]

    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('NEW_OTHER', 'New Other'),
        ('NEW_WITH_DEFECTS', 'New with Defects'),
        ('MANUFACTURER_REFURBISHED', 'Manufacturer Refurbished'),
        ('CERTIFIED_REFURBISHED', 'Certified Refurbished'),
        ('SELLER_REFURBISHED', 'Seller Refurbished'),
        ('LIKE_NEW', 'Like New'),
        ('USED_EXCELLENT', 'Used - Excellent'),
        ('USED_VERY_GOOD', 'Used - Very Good'),
        ('USED_GOOD', 'Used - Good'),
        ('USED_ACCEPTABLE', 'Used - Acceptable'),
        ('FOR_PARTS_OR_NOT_WORKING', 'For Parts or Not Working'),
    ]

    # Core fields
    photo_batch = models.ForeignKey(
        PhotoBatch,
        on_delete=models.CASCADE,
        related_name='ebay_candidates',
        help_text='Source photo batch for this listing'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text='Current status of the listing'
    )

    # eBay specific fields
    category_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='eBay category ID'
    )
    ebay_item_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text='eBay item ID once listed'
    )
    ebay_offer_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='eBay offer ID'
    )
    condition = models.CharField(
        max_length=50,
        choices=CONDITION_CHOICES,
        blank=True,
        help_text='Item condition'
    )

    # Listing content
    title = models.CharField(
        max_length=80,
        blank=True,
        help_text='eBay listing title (max 80 chars)'
    )
    description_md = models.TextField(
        blank=True,
        help_text='Markdown description'
    )
    specifics = models.JSONField(
        default=dict,
        blank=True,
        help_text='Item specifics (key-value pairs)'
    )
    analysis_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Latest structured analysis snapshot (brand/model/keywords etc.)'
    )

    # Pricing
    price_suggested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='AI-suggested price based on comps'
    )
    price_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Final listing price (includes shipping)'
    )
    comps = models.JSONField(
        default=list,
        blank=True,
        help_text='Comparable listings data'
    )

    # Media
    photos = models.JSONField(
        default=list,
        blank=True,
        help_text='Ordered list of photo URLs for eBay'
    )

    # Policies
    policies = models.JSONField(
        default=dict,
        blank=True,
        help_text='Business policies (shipping, return, payment)'
    )

    # Flags
    heavy_flag = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Requires special handling (heavy/oversized)'
    )

    # Logs
    logs = models.JSONField(
        default=list,
        blank=True,
        help_text='Operation logs (API calls, errors, etc.)'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    prepared_at = models.DateTimeField(null=True, blank=True)
    listed_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'eBay Candidate'
        verbose_name_plural = 'eBay Candidates'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['photo_batch', 'status']),
        ]

    def __str__(self):
        title = self.title or f'Candidate #{self.pk}'
        return f'{title} ({self.get_status_display()})'

    def add_log(self, level: str, message: str, data: dict = None):
        """Add a log entry."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,  # info, warning, error
            'message': message,
        }
        if data:
            log_entry['data'] = data

        if not isinstance(self.logs, list):
            self.logs = []
        self.logs.append(log_entry)
        self.save(update_fields=['logs', 'updated_at'])

    @property
    def is_published(self):
        """Check if currently published on eBay."""
        return self.status == 'listed' and bool(self.ebay_item_id)

    @property
    def missing_required_fields(self):
        """List of required fields that are missing."""
        missing = []
        if not self.title:
            missing.append('title')
        if not self.category_id:
            missing.append('category_id')
        if not self.condition:
            missing.append('condition')
        if not self.price_final:
            missing.append('price_final')
        if not self.photos:
            missing.append('photos')
        return missing


class EbayToken(models.Model):
    """
    eBay OAuth tokens storage.
    """

    account = models.CharField(
        max_length=50,
        default='default',
        unique=True,
        help_text='Account identifier'
    )

    # OAuth tokens
    access_token = models.TextField(
        blank=True,
        help_text='eBay OAuth access token'
    )
    refresh_token = models.TextField(
        blank=True,
        help_text='eBay OAuth refresh token'
    )

    # Token expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Access token expiration timestamp'
    )

    # Environment
    sandbox = models.BooleanField(
        default=True,
        help_text='Use sandbox environment'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'eBay Token'
        verbose_name_plural = 'eBay Tokens'

    def __str__(self):
        env = 'sandbox' if self.sandbox else 'production'
        return f'{self.account} ({env})'

    @property
    def is_expired(self):
        """Check if access token is expired."""
        if not self.expires_at:
            return True
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid and not expired."""
        return bool(self.access_token) and not self.is_expired
