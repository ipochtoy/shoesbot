from django.db import models
from django.utils import timezone
import json


class PhotoBatch(models.Model):
    """Карточка товара - батч фото загруженных из Telegram бота."""
    correlation_id = models.CharField(max_length=32, unique=True, db_index=True, verbose_name='ID карточки')
    chat_id = models.BigIntegerField(db_index=True, verbose_name='Chat ID')
    message_ids = models.JSONField(default=list, verbose_name='ID сообщений')  # Telegram message IDs for deletion
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='Загружено')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Обработано')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает'),
            ('processed', 'Обработано'),
            ('failed', 'Ошибка'),
        ],
        default='pending',
        verbose_name='Статус'
    )
    
    # Описание товара (как на eBay)
    title = models.CharField(max_length=500, blank=True, verbose_name='Название товара')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена')
    condition = models.CharField(
        max_length=50,
        choices=[
            ('new', 'Новое'),
            ('used', 'Б/у'),
            ('refurbished', 'Восстановленное'),
        ],
        blank=True,
        verbose_name='Состояние'
    )
    category = models.CharField(max_length=200, blank=True, verbose_name='Категория')
    brand = models.CharField(max_length=200, blank=True, verbose_name='Бренд')
    size = models.CharField(max_length=100, blank=True, verbose_name='Размер')
    color = models.CharField(max_length=100, blank=True, verbose_name='Цвет')
    sku = models.CharField(max_length=200, blank=True, verbose_name='SKU/Артикул')
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Карточка товара'
        verbose_name_plural = 'Карточки товаров'
    
    def __str__(self):
        return f"Карточка {self.correlation_id} ({self.get_status_display()})"
    
    def get_gg_labels(self):
        """Получить все GG лейбы из всех фото этого батча."""
        gg_labels = []
        for photo in self.photos.all():
            for barcode in photo.barcodes.filter(source='gg-label'):
                if barcode.data not in gg_labels:
                    gg_labels.append(barcode.data)
            # Также проверяем Q-коды как GG
            for barcode in photo.barcodes.filter(symbology='CODE39', data__startswith='Q'):
                if barcode.data not in gg_labels:
                    gg_labels.append(barcode.data)
        return gg_labels
    
    def get_all_barcodes(self):
        """Получить все баркоды (кроме GG) из всех фото."""
        barcodes = []
        for photo in self.photos.all():
            for barcode in photo.barcodes.exclude(source='gg-label').exclude(symbology='CODE39', data__startswith='Q'):
                barcodes.append(barcode)
        return barcodes


class Photo(models.Model):
    """Фото из карточки товара."""
    batch = models.ForeignKey(PhotoBatch, related_name='photos', on_delete=models.CASCADE, verbose_name='Карточка товара')
    file_id = models.CharField(max_length=255, verbose_name='File ID')  # Telegram file_id
    message_id = models.BigIntegerField(verbose_name='Message ID')
    image = models.ImageField(upload_to='photos/%Y/%m/%d/', verbose_name='Изображение')
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='Загружено')
    is_main = models.BooleanField(default=False, verbose_name='Главное фото')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    
    class Meta:
        ordering = ['-is_main', 'order', 'uploaded_at']
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото'
    
    def __str__(self):
        return f"Фото {self.id} (карточка {self.batch.correlation_id})"
    
    def save(self, *args, **kwargs):
        # Если это главное фото, убираем главный статус у остальных
        if self.is_main:
            Photo.objects.filter(batch=self.batch, is_main=True).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)


class BarcodeResult(models.Model):
    """Баркод найденный на фото."""
    photo = models.ForeignKey(Photo, related_name='barcodes', on_delete=models.CASCADE, verbose_name='Фото')
    symbology = models.CharField(max_length=50, verbose_name='Тип')
    data = models.CharField(max_length=500, verbose_name='Код')
    source = models.CharField(max_length=50, verbose_name='Источник')  # zbar, opencv-qr, vision-ocr, gg-label
    
    class Meta:
        unique_together = [['photo', 'symbology', 'data']]
        verbose_name = 'Баркод'
        verbose_name_plural = 'Баркоды'
    
    def __str__(self):
        return f"{self.symbology}: {self.data} ({self.source})"


class ProcessingTask(models.Model):
    """Задача обработки фото внешними API."""
    photo = models.ForeignKey(Photo, related_name='processing_tasks', on_delete=models.CASCADE, verbose_name='Фото')
    api_name = models.CharField(max_length=100, verbose_name='API')  # e.g., 'google-vision', 'azure-cv', etc.
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает'),
            ('processing', 'Обрабатывается'),
            ('completed', 'Завершено'),
            ('failed', 'Ошибка'),
        ],
        default='pending',
        verbose_name='Статус'
    )
    request_data = models.JSONField(null=True, blank=True, verbose_name='Запрос')
    response_data = models.JSONField(null=True, blank=True, verbose_name='Ответ')
    error_message = models.TextField(null=True, blank=True, verbose_name='Ошибка')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Создано')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершено')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Задача обработки'
        verbose_name_plural = 'Задачи обработки'
    
    def __str__(self):
        return f"{self.api_name} для фото {self.photo.id} ({self.get_status_display()})"
