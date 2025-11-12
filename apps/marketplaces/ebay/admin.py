"""
eBay marketplace admin interface.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib import messages
from .models import EbayCandidate, EbayToken


@admin.register(EbayCandidate)
class EbayCandidateAdmin(admin.ModelAdmin):
    """
    Admin interface for eBay listing candidates.
    """

    list_display = [
        'id',
        'title_display',
        'photo_batch_link',
        'status_badge',
        'condition',
        'category_display',
        'price_display',
        'heavy_badge',
        'created_at',
    ]

    list_filter = [
        'status',
        'condition',
        'heavy_flag',
        'created_at',
        'listed_at',
    ]

    search_fields = [
        'title',
        'ebay_item_id',
        'photo_batch__title',
        'photo_batch__sku',
        'photo_batch__correlation_id',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'prepared_at',
        'listed_at',
        'ended_at',
        'logs_display',
        'missing_fields_display',
    ]

    fieldsets = [
        ('Basic Info', {
            'fields': (
                'photo_batch',
                'status',
                'heavy_flag',
            )
        }),
        ('eBay Listing', {
            'fields': (
                'title',
                'category_id',
                'condition',
                'description_md',
                'specifics',
                'ebay_item_id',
            )
        }),
        ('Pricing', {
            'fields': (
                'price_suggested',
                'price_final',
                'comps',
            )
        }),
        ('Media & Policies', {
            'fields': (
                'photos',
                'policies',
            )
        }),
        ('System Info', {
            'fields': (
                'created_at',
                'updated_at',
                'prepared_at',
                'listed_at',
                'ended_at',
                'missing_fields_display',
                'logs_display',
            ),
            'classes': ('collapse',),
        }),
    ]

    actions = [
        'action_delete_from_list',
        'action_publish',
        'action_end',
        'action_reprice',
        'action_prepare',
    ]

    def title_display(self, obj):
        """Display title with truncation."""
        title = obj.title or f'Candidate #{obj.pk}'
        if len(title) > 50:
            return f'{title[:50]}...'
        return title
    title_display.short_description = 'Title'

    def photo_batch_link(self, obj):
        """Link to eBay edit page and source photo batch."""
        links = []
        # Link to eBay edit page
        edit_url = reverse('ebay:candidate-edit', args=[obj.pk])
        links.append(f'<a href="{edit_url}" style="font-weight: bold; color: #17a2b8;">✏️ Edit</a>')
        
        # Link to source photo batch
        if obj.photo_batch:
            url = reverse('admin:photos_photobatch_change', args=[obj.photo_batch.pk])
            title = obj.photo_batch.title or obj.photo_batch.correlation_id
            links.append(f'<a href="{url}">{title[:30]}</a>')
        
        return format_html(' | '.join(links)) if links else '-'
    photo_batch_link.short_description = 'Actions'

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'draft': '#6c757d',      # gray
            'ready': '#17a2b8',      # blue
            'listed': '#28a745',     # green
            'error': '#dc3545',      # red
            'ended': '#ffc107',      # yellow
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'

    def category_display(self, obj):
        """Display category ID."""
        if obj.category_id:
            return obj.category_id
        return format_html('<span style="color: #dc3545;">Not set</span>')
    category_display.short_description = 'Category'

    def price_display(self, obj):
        """Display pricing info."""
        if obj.price_final:
            suggested = f'${obj.price_suggested}' if obj.price_suggested else '-'
            return format_html(
                '<strong>${}</strong><br><small style="color: #6c757d;">suggested: {}</small>',
                obj.price_final,
                suggested
            )
        return '-'
    price_display.short_description = 'Price'

    def heavy_badge(self, obj):
        """Display heavy flag badge."""
        if obj.heavy_flag:
            return format_html(
                '<span style="background-color: #ffc107; color: #000; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px; font-weight: bold;">HEAVY</span>'
            )
        return ''
    heavy_badge.short_description = 'Heavy'

    def logs_display(self, obj):
        """Display logs in formatted way."""
        if not obj.logs:
            return 'No logs'

        html = '<div style="max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 11px;">'
        for log in obj.logs:
            timestamp = log.get('timestamp', '')
            level = log.get('level', 'info').upper()
            message = log.get('message', '')

            color = {
                'INFO': '#17a2b8',
                'WARNING': '#ffc107',
                'ERROR': '#dc3545',
            }.get(level, '#6c757d')

            html += f'<div style="margin-bottom: 5px;">'
            html += f'<span style="color: #6c757d;">[{timestamp}]</span> '
            html += f'<span style="color: {color}; font-weight: bold;">{level}</span>: '
            html += f'{message}'
            html += '</div>'

        html += '</div>'
        return format_html(html)
    logs_display.short_description = 'Logs'

    def missing_fields_display(self, obj):
        """Display missing required fields."""
        missing = obj.missing_required_fields
        if not missing:
            return format_html('<span style="color: #28a745;">✓ All required fields filled</span>')

        return format_html(
            '<span style="color: #dc3545;">Missing: {}</span>',
            ', '.join(missing)
        )
    missing_fields_display.short_description = 'Required Fields'

    # Admin actions

    @admin.action(description='❌ Delete from eBay list')
    def action_delete_from_list(self, request, queryset):
        """Delete candidates from the list."""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'Deleted {count} candidate(s) from eBay list.',
            messages.SUCCESS
        )

    @admin.action(description='🚀 Publish to eBay')
    def action_publish(self, request, queryset):
        """Publish candidates to eBay."""
        from .tasks import publish_candidate

        published = 0
        errors = []

        for candidate in queryset:
            if candidate.status == 'listed':
                errors.append(f'{candidate}: Already listed')
                continue

            if candidate.missing_required_fields:
                errors.append(f'{candidate}: Missing required fields - {", ".join(candidate.missing_required_fields)}')
                continue

            # Trigger celery task
            publish_candidate.delay(candidate.id)
            published += 1

        if published:
            self.message_user(
                request,
                f'Publishing {published} candidate(s) to eBay...',
                messages.SUCCESS
            )

        if errors:
            self.message_user(
                request,
                'Errors: ' + '; '.join(errors),
                messages.WARNING
            )

    @admin.action(description='🛑 End eBay listings')
    def action_end(self, request, queryset):
        """End active eBay listings."""
        from .tasks import end_candidate

        ended = 0
        errors = []

        for candidate in queryset:
            if candidate.status != 'listed':
                errors.append(f'{candidate}: Not listed')
                continue

            if not candidate.ebay_item_id:
                errors.append(f'{candidate}: No eBay item ID')
                continue

            # Trigger celery task
            end_candidate.delay(candidate.id)
            ended += 1

        if ended:
            self.message_user(
                request,
                f'Ending {ended} listing(s)...',
                messages.SUCCESS
            )

        if errors:
            self.message_user(
                request,
                'Errors: ' + '; '.join(errors),
                messages.WARNING
            )

    @admin.action(description='💰 Reprice to market median')
    def action_reprice(self, request, queryset):
        """Reprice listings based on current market median."""
        from .tasks import reprice_candidate

        repriced = 0
        for candidate in queryset.filter(status='listed'):
            reprice_candidate.delay(candidate.id)
            repriced += 1

        self.message_user(
            request,
            f'Repricing {repriced} listing(s)...',
            messages.SUCCESS
        )

    @admin.action(description='⚙️ Prepare listing (AI pipeline)')
    def action_prepare(self, request, queryset):
        """Run preparation pipeline on candidates."""
        from .tasks import prepare_candidate

        prepared = 0
        for candidate in queryset.filter(status='draft'):
            prepare_candidate.delay(candidate.id)
            prepared += 1

        self.message_user(
            request,
            f'Preparing {prepared} candidate(s)...',
            messages.SUCCESS
        )


@admin.register(EbayToken)
class EbayTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for eBay OAuth tokens.
    """

    list_display = [
        'account',
        'environment',
        'token_status',
        'expires_at',
        'updated_at',
    ]

    list_filter = [
        'sandbox',
        'created_at',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'token_status_display',
    ]

    fieldsets = [
        ('Account', {
            'fields': (
                'account',
                'sandbox',
            )
        }),
        ('Tokens', {
            'fields': (
                'access_token',
                'refresh_token',
                'expires_at',
                'token_status_display',
            )
        }),
        ('System Info', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    ]

    def environment(self, obj):
        """Display environment."""
        if obj.sandbox:
            return format_html(
                '<span style="background-color: #ffc107; color: #000; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">SANDBOX</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">PRODUCTION</span>'
        )
    environment.short_description = 'Environment'

    def token_status(self, obj):
        """Display token validity status."""
        if obj.is_valid:
            return format_html('<span style="color: #28a745;">✓ Valid</span>')
        elif obj.is_expired:
            return format_html('<span style="color: #ffc107;">⚠ Expired</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ Invalid</span>')
    token_status.short_description = 'Status'

    def token_status_display(self, obj):
        """Detailed token status display."""
        if obj.is_valid:
            time_left = obj.expires_at - timezone.now()
            return format_html(
                '<span style="color: #28a745;">✓ Valid (expires in {})</span>',
                str(time_left).split('.')[0]
            )
        elif obj.is_expired:
            return format_html('<span style="color: #ffc107;">⚠ Token expired - needs refresh</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ No valid token</span>')
    token_status_display.short_description = 'Token Status'


# Customize admin site
admin.site.site_header = 'eBay Marketplace Admin'
admin.site.index_title = 'eBay Integration'
