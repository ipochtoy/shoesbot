from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import PhotoBatch, Photo, BarcodeResult, ProcessingTask


@admin.register(PhotoBatch)
class PhotoBatchAdmin(admin.ModelAdmin):
    list_display = ['correlation_id_link', 'product_title', 'gg_labels', 'chat_id', 'status', 'uploaded_at', 'photo_previews', 'photo_count']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['correlation_id', 'chat_id', 'title', 'description']
    readonly_fields = ['correlation_id', 'uploaded_at', 'processed_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('correlation_id', 'chat_id', 'status', 'uploaded_at', 'processed_at')
        }),
        ('Описание товара', {
            'fields': ('title', 'description', 'price', 'condition', 'category', 'brand', 'size', 'color', 'sku')
        }),
    )
    
    def correlation_id_link(self, obj):
        """Клик по ID карточки открывает детальную страницу."""
        url = reverse('product_card_detail', args=[obj.id])
        return format_html('<a href="{}" style="font-weight: bold; font-size: 14px;">{}</a>', url, obj.correlation_id)
    correlation_id_link.short_description = 'ID карточки'
    correlation_id_link.admin_order_field = 'correlation_id'
    
    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Фото'
    
    def product_title(self, obj):
        """Показываем название товара."""
        if obj.title:
            # Обрезаем длинные названия
            title = obj.title if len(obj.title) <= 50 else obj.title[:47] + '...'
            return format_html('<span style="font-weight: 500;">{}</span>', title)
        return format_html('<span style="color: #999; font-style: italic;">—</span>')
    product_title.short_description = 'Название товара'
    product_title.admin_order_field = 'title'
    
    def gg_labels(self, obj):
        """Показываем GG лейбы."""
        labels = obj.get_gg_labels()
        if labels:
            # Фильтруем только те что начинаются с GG
            gg_only = [label for label in labels if label.startswith('GG')]
            if gg_only:
                labels_str = ', '.join(gg_only)
                return format_html(
                    '<span style="background: #fff3cd; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: #856404;">{}</span>',
                    labels_str
                )
        return format_html('<span style="color: #999;">—</span>')
    gg_labels.short_description = 'Наша лейба'
    
    def photo_previews(self, obj):
        """Показываем маленькие превью фото."""
        photos = obj.photos.all()[:4]  # Первые 4 фото
        if not photos:
            return "-"
        previews = []
        for photo in photos:
            if photo.image:
                previews.append(
                    format_html(
                        '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; margin: 2px; border: 1px solid #ddd; border-radius: 4px;" />',
                        photo.image.url
                    )
                )
        return format_html(''.join(previews))
    photo_previews.short_description = 'Превью'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('photos', 'photos__barcodes')


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'batch_link', 'message_id', 'uploaded_at', 'barcode_count', 'image_preview', 'process_actions']
    list_filter = ['uploaded_at', 'batch__status']
    search_fields = ['batch__correlation_id', 'file_id', 'message_id']
    readonly_fields = ['uploaded_at', 'image_preview']
    fields = ['batch', 'file_id', 'message_id', 'image', 'image_preview', 'uploaded_at']
    actions = ['create_google_vision_task', 'create_azure_cv_task']
    
    def batch_link(self, obj):
        url = reverse('admin:photos_photobatch_change', args=[obj.batch.id])
        return format_html('<a href="{}">{}</a>', url, obj.batch.correlation_id)
    batch_link.short_description = 'Карточка товара'
    
    def barcode_count(self, obj):
        count = obj.barcodes.count()
        if count > 0:
            url = reverse('admin:photos_barcoderesult_changelist') + f'?photo__id__exact={obj.id}'
            return format_html('<a href="{}">{} кодов</a>', url, count)
        return count
    barcode_count.short_description = 'Баркоды'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'
    
    def process_actions(self, obj):
        tasks_url = reverse('admin:photos_processingtask_changelist') + f'?photo__id__exact={obj.id}'
        add_vision_url = reverse('admin:photos_processingtask_add') + f'?photo={obj.id}&api_name=google-vision'
        add_azure_url = reverse('admin:photos_processingtask_add') + f'?photo={obj.id}&api_name=azure-cv'
        return format_html(
            '<a href="{}">Задачи</a> | <a href="{}">+ Vision</a> | <a href="{}">+ Azure</a>',
            tasks_url, add_vision_url, add_azure_url
        )
    process_actions.short_description = 'Задачи'
    
    @admin.action(description='Создать задачу Google Vision для выбранных фото')
    def create_google_vision_task(self, request, queryset):
        created = 0
        for photo in queryset:
            task, was_created = ProcessingTask.objects.get_or_create(
                photo=photo,
                api_name='google-vision',
                defaults={'status': 'pending'}
            )
            if was_created:
                created += 1
        self.message_user(request, f'Создано {created} задач Google Vision.')
    
    @admin.action(description='Создать задачу Azure CV для выбранных фото')
    def create_azure_cv_task(self, request, queryset):
        created = 0
        for photo in queryset:
            task, was_created = ProcessingTask.objects.get_or_create(
                photo=photo,
                api_name='azure-cv',
                defaults={'status': 'pending'}
            )
            if was_created:
                created += 1
        self.message_user(request, f'Создано {created} задач Azure CV.')


@admin.register(BarcodeResult)
class BarcodeResultAdmin(admin.ModelAdmin):
    list_display = ['symbology', 'data', 'source', 'photo_link', 'batch_link']
    list_filter = ['source', 'symbology']
    search_fields = ['data', 'symbology']
    readonly_fields = ['photo_link']
    
    def photo_link(self, obj):
        url = reverse('admin:photos_photo_change', args=[obj.photo.id])
        return format_html('<a href="{}">Photo {}</a>', url, obj.photo.id)
    photo_link.short_description = 'Photo'
    
    def batch_link(self, obj):
        return obj.photo.batch.correlation_id
    batch_link.short_description = 'Карточка товара'


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ['api_name', 'photo_link', 'status', 'created_at', 'completed_at', 'task_actions']
    list_filter = ['status', 'api_name', 'created_at']
    search_fields = ['photo__batch__correlation_id', 'api_name']
    readonly_fields = ['created_at', 'completed_at', 'request_data_display', 'response_data_display']
    fields = ['photo', 'api_name', 'status', 'request_data', 'request_data_display', 
              'response_data', 'response_data_display', 'error_message', 'created_at', 'completed_at']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Pre-fill photo and api_name from query params
        if obj is None and 'photo' in request.GET:
            form.base_fields['photo'].initial = request.GET.get('photo')
        if obj is None and 'api_name' in request.GET:
            form.base_fields['api_name'].initial = request.GET.get('api_name')
        return form
    
    def photo_link(self, obj):
        url = reverse('admin:photos_photo_change', args=[obj.photo.id])
        return format_html('<a href="{}">Photo {}</a>', url, obj.photo.id)
    photo_link.short_description = 'Photo'
    
    def request_data_display(self, obj):
        if obj.request_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.request_data, indent=2))
        return "-"
    request_data_display.short_description = 'Request (formatted)'
    
    def response_data_display(self, obj):
        if obj.response_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.response_data, indent=2))
        return "-"
    response_data_display.short_description = 'Response (formatted)'
    
    def task_actions(self, obj):
        if obj.status == 'pending':
            url = reverse('process_task', args=[obj.id])
            return format_html('<a href="{}">Обработать</a>', url)
        return obj.get_status_display()
    task_actions.short_description = 'Действия'
