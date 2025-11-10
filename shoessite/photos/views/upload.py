"""
Upload views - функции загрузки фотографий.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.db.models import Max
from ..models import PhotoBatch, Photo, BarcodeResult, PhotoBuffer
import json
import uuid
import base64
import requests
from io import BytesIO
from PIL import Image


@csrf_exempt
@require_http_methods(["POST"])
def upload_batch(request):
    """API endpoint for Telegram bot to upload photo batch."""
    try:
        data = json.loads(request.body)

        correlation_id = data.get('correlation_id') or uuid.uuid4().hex[:8]
        chat_id = data.get('chat_id')
        message_ids = data.get('message_ids', [])
        photos_data = data.get('photos', [])
        barcodes = data.get('barcodes', [])

        if not chat_id or not photos_data:
            return JsonResponse({'error': 'chat_id and photos required'}, status=400)

        # Create or get batch
        batch, created = PhotoBatch.objects.get_or_create(
            correlation_id=correlation_id,
            defaults={
                'chat_id': chat_id,
                'message_ids': message_ids,
                'status': 'processed' if barcodes else 'pending',
            }
        )

        if not created:
            batch.message_ids = message_ids
            batch.status = 'processed' if barcodes else 'pending'
            batch.processed_at = timezone.now()
            batch.save()

        # Process photos
        photo_objects = []
        for idx, photo_data in enumerate(photos_data):
            file_id = photo_data.get('file_id')
            message_id = photo_data.get('message_id')
            image_data = photo_data.get('image')  # base64 encoded

            if not file_id or not image_data:
                continue

            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_data.split(',')[-1] if ',' in image_data else image_data)
                photo = Photo.objects.create(
                    batch=batch,
                    file_id=file_id,
                    message_id=message_id,
                )
                photo.image.save(
                    f'{correlation_id}_{idx}.jpg',
                    ContentFile(image_bytes),
                    save=True
                )
                photo_objects.append(photo)
            except Exception as e:
                print(f"Error processing photo {idx}: {e}")
                continue

        # Save barcodes
        barcode_count = 0
        for barcode_data in barcodes:
            photo_idx = barcode_data.get('photo_index', 0)
            if photo_idx < len(photo_objects):
                BarcodeResult.objects.get_or_create(
                    photo=photo_objects[photo_idx],
                    symbology=barcode_data.get('symbology', ''),
                    data=barcode_data.get('data', ''),
                    defaults={
                        'source': barcode_data.get('source', 'unknown'),
                    }
                )
                barcode_count += 1

        # Автоматически отправляем в Pochtoy API
        pochtoy_message = None
        try:
            from ..pochtoy_integration import send_card_to_pochtoy
            pochtoy_result = send_card_to_pochtoy(batch)
            print(f"Pochtoy auto-send result: {pochtoy_result}")

            if pochtoy_result:
                if pochtoy_result.get('success'):
                    pochtoy_message = f"✅ {pochtoy_result.get('message', 'Товар успешно добавлен')}"
                else:
                    pochtoy_message = f"❌ Ошибка Pochtoy: {pochtoy_result.get('error', 'Неизвестная ошибка')}"
        except Exception as e:
            print(f"Pochtoy auto-send error: {e}")
            pochtoy_message = f"❌ Pochtoy недоступен: {str(e)}"

        return JsonResponse({
            'success': True,
            'correlation_id': correlation_id,
            'photos_saved': len(photo_objects),
            'barcodes_saved': barcode_count,
            'pochtoy_message': pochtoy_message,  # Для Telegram бота
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def upload_photo_from_computer(request, card_id):
    """Добавить фото к карточке с компьютера."""
    try:
        card = get_object_or_404(PhotoBatch, id=card_id)

        if 'photo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Фото не выбрано'}, status=400)

        uploaded_file = request.FILES['photo']

        # Проверяем тип файла
        if not uploaded_file.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Файл должен быть изображением'}, status=400)

        # Проверяем размер (макс 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Размер файла не должен превышать 10MB'}, status=400)

        # Читаем и обрабатываем изображение
        try:
            image_data = uploaded_file.read()
            img = Image.open(BytesIO(image_data))

            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Сохраняем в BytesIO
            output = BytesIO()
            img.save(output, format='JPEG', quality=90)
            output.seek(0)

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка обработки изображения: {str(e)}'}, status=400)

        # Определяем порядок для нового фото (последний)
        max_order = Photo.objects.filter(batch=card).aggregate(Max('order'))['order__max'] or 0

        # Создаем Photo объект
        photo = Photo.objects.create(
            batch=card,
            file_id=f'upload_{uuid.uuid4().hex[:12]}',
            message_id=0,
            order=max_order + 1,
        )

        # Сохраняем изображение
        filename = f'{card.correlation_id}_upload_{photo.id}.jpg'
        photo.image.save(filename, ContentFile(output.read()), save=True)

        return JsonResponse({
            'success': True,
            'photo_id': photo.id,
            'photo_url': photo.image.url
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_photo_from_url(request, card_id):
    """Добавить фото к карточке из URL."""
    try:
        card = get_object_or_404(PhotoBatch, id=card_id)
        data = json.loads(request.body)
        image_url = data.get('url')

        if not image_url:
            return JsonResponse({'success': False, 'error': 'URL не указан'}, status=400)

        # Скачиваем изображение
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(image_url, headers=headers, timeout=15, stream=True)

        if not resp.ok:
            return JsonResponse({'success': False, 'error': f'Не удалось скачать изображение: {resp.status_code}'}, status=400)

        # Проверяем Content-Type
        content_type = resp.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'URL не является изображением'}, status=400)

        # Читаем изображение
        image_data = resp.content

        # Проверяем и обрабатываем изображение
        try:
            img = Image.open(BytesIO(image_data))
            img.verify()

            # Конвертируем в RGB если нужно
            img = Image.open(BytesIO(image_data))
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Сохраняем в BytesIO
            output = BytesIO()
            img.save(output, format='JPEG', quality=90)
            output.seek(0)

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка обработки изображения: {str(e)}'}, status=400)

        # Определяем порядок для нового фото (последний)
        max_order = Photo.objects.filter(batch=card).aggregate(Max('order'))['order__max'] or 0

        # Создаем Photo объект
        photo = Photo.objects.create(
            batch=card,
            file_id=f'url_{uuid.uuid4().hex[:12]}',
            message_id=0,
            order=max_order + 1,
        )

        # Сохраняем изображение
        filename = f'{card.correlation_id}_stock_{photo.id}.jpg'
        photo.image.save(filename, ContentFile(output.read()), save=True)

        return JsonResponse({
            'success': True,
            'photo_id': photo.id,
            'photo_url': photo.image.url
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def buffer_upload(request):
    """API для буферного бота - сохраняет фото без обработки."""
    try:
        data = json.loads(request.body)

        file_id = data.get('file_id')
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')
        image_b64 = data.get('image')
        gg_label = data.get('gg_label', '')

        if not all([file_id, message_id, chat_id, image_b64]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Проверяем что такого фото еще нет
        if PhotoBuffer.objects.filter(file_id=file_id).exists():
            return JsonResponse({'success': True, 'message': 'Already exists'})

        # Декодируем base64
        image_bytes = base64.b64decode(image_b64)

        # Создаем запись с GG лейблом
        photo_buffer = PhotoBuffer.objects.create(
            file_id=file_id,
            message_id=message_id,
            chat_id=chat_id,
            gg_label=gg_label,
        )

        # Сохраняем изображение
        photo_buffer.image.save(
            f'buffer_{photo_buffer.id}.jpg',
            ContentFile(image_bytes),
            save=True
        )

        print(f"✅ Saved photo {photo_buffer.id} to buffer")

        return JsonResponse({
            'success': True,
            'photo_id': photo_buffer.id
        })

    except Exception as e:
        import traceback
        print(f"Error in buffer_upload: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
