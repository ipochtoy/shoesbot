"""
eBay marketplace DRF serializers.
"""
from rest_framework import serializers
from .models import EbayCandidate, EbayToken
from photos.models import PhotoBatch


class PhotoBatchMiniSerializer(serializers.ModelSerializer):
    """Minimal PhotoBatch serializer for nested display."""

    class Meta:
        model = PhotoBatch
        fields = ['id', 'correlation_id', 'title', 'sku', 'brand']
        read_only_fields = fields


class EbayCandidateListSerializer(serializers.ModelSerializer):
    """Serializer for listing eBay candidates."""

    photo_batch = PhotoBatchMiniSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    is_published = serializers.BooleanField(read_only=True)
    missing_fields = serializers.ListField(source='missing_required_fields', read_only=True)

    class Meta:
        model = EbayCandidate
        fields = [
            'id',
            'photo_batch',
            'status',
            'status_display',
            'title',
            'category_id',
            'condition',
            'condition_display',
            'price_suggested',
            'price_final',
            'ebay_item_id',
            'heavy_flag',
            'is_published',
            'missing_fields',
            'created_at',
            'updated_at',
            'listed_at',
        ]
        read_only_fields = [
            'id',
            'status_display',
            'condition_display',
            'is_published',
            'missing_fields',
            'created_at',
            'updated_at',
            'listed_at',
        ]


class EbayCandidateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for eBay candidate CRUD operations."""

    photo_batch = PhotoBatchMiniSerializer(read_only=True)
    photo_batch_id = serializers.PrimaryKeyRelatedField(
        queryset=PhotoBatch.objects.all(),
        source='photo_batch',
        write_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    is_published = serializers.BooleanField(read_only=True)
    missing_fields = serializers.ListField(source='missing_required_fields', read_only=True)

    class Meta:
        model = EbayCandidate
        fields = [
            'id',
            'photo_batch',
            'photo_batch_id',
            'status',
            'status_display',
            'title',
            'description_md',
            'category_id',
            'condition',
            'condition_display',
            'specifics',
            'price_suggested',
            'price_final',
            'comps',
            'photos',
            'policies',
            'ebay_item_id',
            'heavy_flag',
            'is_published',
            'missing_fields',
            'logs',
            'created_at',
            'updated_at',
            'prepared_at',
            'listed_at',
            'ended_at',
        ]
        read_only_fields = [
            'id',
            'status_display',
            'condition_display',
            'is_published',
            'missing_fields',
            'created_at',
            'updated_at',
            'prepared_at',
            'listed_at',
            'ended_at',
            'ebay_item_id',
        ]

    def validate_title(self, value):
        """Validate title length (eBay max 80 chars)."""
        if value and len(value) > 80:
            raise serializers.ValidationError('Title must be 80 characters or less.')
        return value

    def validate_specifics(self, value):
        """Validate item specifics format."""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Specifics must be a dictionary.')
        return value

    def validate_photos(self, value):
        """Validate photos format."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Photos must be a list of URLs.')
        return value


class BulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating eBay candidates."""

    photo_batch_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='List of PhotoBatch IDs to create candidates for'
    )

    def validate_photo_batch_ids(self, value):
        """Validate that all photo batches exist."""
        existing_ids = PhotoBatch.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                f'PhotoBatch IDs not found: {", ".join(map(str, missing_ids))}'
            )

        return value

    def create(self, validated_data):
        """Create EbayCandidate instances for each PhotoBatch."""
        photo_batch_ids = validated_data['photo_batch_ids']
        candidates = []

        for batch_id in photo_batch_ids:
            # Skip if candidate already exists
            if EbayCandidate.objects.filter(photo_batch_id=batch_id).exists():
                continue

            candidate = EbayCandidate.objects.create(
                photo_batch_id=batch_id,
                status='draft',
            )
            candidate.add_log('info', 'Created via bulk API')
            candidates.append(candidate)

        return candidates


class TaxonomySuggestionSerializer(serializers.Serializer):
    """Serializer for category taxonomy suggestions."""

    q = serializers.CharField(
        required=True,
        help_text='Search query for category'
    )


class TaxonomyCategorySerializer(serializers.Serializer):
    """Serializer for eBay category."""

    category_id = serializers.CharField()
    category_name = serializers.CharField()
    category_tree_id = serializers.CharField()
    leaf = serializers.BooleanField(default=True)


class ItemSpecificSerializer(serializers.Serializer):
    """Serializer for item specific field."""

    name = serializers.CharField()
    required = serializers.BooleanField(default=False)
    usage = serializers.CharField(required=False, allow_blank=True)
    values = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    max_values = serializers.IntegerField(required=False, allow_null=True)


class ItemSpecificsResponseSerializer(serializers.Serializer):
    """Serializer for item specifics response."""

    category_id = serializers.CharField()
    specifics = ItemSpecificSerializer(many=True)


class PricingCompsQuerySerializer(serializers.Serializer):
    """Serializer for pricing comps query."""

    q = serializers.CharField(required=False, allow_blank=True, help_text='Search query')
    upc = serializers.CharField(required=False, allow_blank=True, help_text='UPC code')
    ean = serializers.CharField(required=False, allow_blank=True, help_text='EAN code')
    isbn = serializers.CharField(required=False, allow_blank=True, help_text='ISBN code')
    category_id = serializers.CharField(required=False, allow_blank=True, help_text='eBay category ID')

    def validate(self, data):
        """Ensure at least one query parameter is provided."""
        if not any([data.get('q'), data.get('upc'), data.get('ean'), data.get('isbn')]):
            raise serializers.ValidationError(
                'At least one of: q, upc, ean, or isbn must be provided.'
            )
        return data


class CompItemSerializer(serializers.Serializer):
    """Serializer for comparable item."""

    item_id = serializers.CharField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    condition = serializers.CharField()
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    seller_rating = serializers.IntegerField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True)
    url = serializers.URLField(required=False, allow_blank=True)


class PricingCompsResponseSerializer(serializers.Serializer):
    """Serializer for pricing comps response."""

    comps = CompItemSerializer(many=True)
    median = serializers.DecimalField(max_digits=10, decimal_places=2)
    p25 = serializers.DecimalField(max_digits=10, decimal_places=2)
    p75 = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.IntegerField()
    price_suggested = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_final = serializers.DecimalField(max_digits=10, decimal_places=2)


class PrepareResponseSerializer(serializers.Serializer):
    """Serializer for prepare pipeline response."""

    success = serializers.BooleanField()
    status = serializers.CharField()
    message = serializers.CharField()
    missing_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    candidate = EbayCandidateDetailSerializer(required=False, allow_null=True)


class PublishResponseSerializer(serializers.Serializer):
    """Serializer for publish response."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    ebay_item_id = serializers.CharField(required=False, allow_blank=True)
    listing_url = serializers.URLField(required=False, allow_blank=True)
    candidate = EbayCandidateDetailSerializer(required=False, allow_null=True)


class EndResponseSerializer(serializers.Serializer):
    """Serializer for end listing response."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    candidate = EbayCandidateDetailSerializer(required=False, allow_null=True)


class RepriceResponseSerializer(serializers.Serializer):
    """Serializer for reprice response."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    old_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    new_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    candidate = EbayCandidateDetailSerializer(required=False, allow_null=True)


class EbayTokenSerializer(serializers.ModelSerializer):
    """Serializer for eBay OAuth tokens."""

    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = EbayToken
        fields = [
            'id',
            'account',
            'sandbox',
            'expires_at',
            'is_expired',
            'is_valid',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_expired',
            'is_valid',
            'created_at',
            'updated_at',
        ]

    # Don't expose actual tokens in API
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mask tokens
        data['access_token_preview'] = '***' if instance.access_token else None
        data['refresh_token_preview'] = '***' if instance.refresh_token else None
        return data
