"""
Buffer views - функции работы с буфером сортировки фото.
"""
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from ..models import PhotoBuffer, PhotoBatch
import json
import os
import base64


@staff_member_required
def sorting_view(request):
    """Страница сортировки фото (простой интерфейс)."""
    photos = PhotoBuffer.objects.filter(processed=False).order_by('id')

    # Конвертим в JSON для JS
    photos_data = []
    for p in photos:
        photos_data.append({
            'id': p.id,
            'image_url': p.image.url if p.image else '',
            'gg_label': p.gg_label,
            'barcode': p.barcode,
            'group_id': p.group_id,
        })

    return render(request, 'photos/simple_sorting.html', {
        'photos': photos,
        'photos_json': json.dumps(photos_data)
    })


@csrf_exempt
@require_http_methods(["POST"])
def update_photo_group(request, photo_id):
    """Обновить группу фото."""
    try:
        photo = get_object_or_404(PhotoBuffer, id=photo_id)
        data = json.loads(request.body)

        group_id = data.get('group_id')
        photo.group_id = group_id
        photo.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_group_to_bot(request, group_id):
    """Создать карточку напрямую из группы фото (без Telegram)."""
    try:
        from .upload import upload_batch
        import uuid

        # Получаем фото группы
        group_photos = PhotoBuffer.objects.filter(group_id=group_id, processed=False).order_by('id')

        if not group_photos.exists():
            return JsonResponse({'error': 'Группа пуста'}, status=400)

        # Создаем correlation_id
        corr_id = uuid.uuid4().hex[:8]

        chat_id = group_photos.first().chat_id

        # Подготавливаем фото для upload_batch
        photos_data = []
        for idx, p in enumerate(group_photos):
            # Читаем изображение
            with p.image.open('rb') as f:
                image_data = f.read()

            photos_data.append({
                'file_id': p.file_id,
                'message_id': p.message_id,
                'image': base64.b64encode(image_data).decode('utf-8'),
            })

        # Создаем карточку напрямую через upload_batch
        batch_data = {
            'correlation_id': corr_id,
            'chat_id': chat_id,
            'message_ids': [p.message_id for p in group_photos],
            'photos': photos_data,
            'barcodes': []  # Баркоды будут распознаны автоматически
        }

        # Вызываем upload_batch напрямую
        from django.test import RequestFactory
        factory = RequestFactory()
        batch_request = factory.post('/photos/api/upload-batch/',
                                     data=json.dumps(batch_data),
                                     content_type='application/json')

        # Вызываем функцию напрямую
        batch_response = upload_batch(batch_request)
        batch_result = json.loads(batch_response.content)

        print(f"Upload batch result: {batch_result}")

        if batch_result.get('success'):
            # Помечаем как обработанные
            group_photos.update(sent_to_bot=True, processed=True)

            return JsonResponse({
                'success': True,
                'correlation_id': corr_id,
                'photos_sent': len(photos_data),
                'card_created': True
            })
        else:
            return JsonResponse({'error': batch_result.get('error', 'Unknown error')}, status=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def detect_gg_in_buffer(request):
    """Распознать GG лейблы на всех фото в буфере."""
    try:
        import requests as sync_requests

        photos = PhotoBuffer.objects.filter(processed=False, gg_label='')
        found_count = 0

        for photo in photos:
            try:
                # Читаем изображение
                with photo.image.open('rb') as f:
                    image_data = f.read()

                img_b64 = base64.b64encode(image_data).decode('utf-8')

                # Спрашиваем OpenAI
                openai_key = os.getenv('OPENAI_API_KEY')
                if not openai_key:
                    continue

                resp = sync_requests.post('https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {openai_key}'},
                    json={
                        'model': 'gpt-4o-mini',
                        'messages': [{
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': 'Find GG label on this image (like GG681, GG700, Q747). Return ONLY the code, nothing else. If no GG label - return "none".'},
                                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                            ]
                        }],
                        'max_tokens': 20
                    },
                    timeout=10
                )

                if resp.status_code == 200:
                    text = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip().upper()
                    if text and text != 'NONE' and ('GG' in text or 'Q' in text):
                        photo.gg_label = text
                        photo.save()
                        found_count += 1
                        print(f"Found GG {text} on photo {photo.id}")

            except Exception as e:
                print(f"Error detecting GG on photo {photo.id}: {e}")
                continue

        return JsonResponse({
            'success': True,
            'found_count': found_count
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_group_to_pochtoy(request, group_id):
    """Отправить группу фото в Pochtoy API."""
    try:
        from ..pochtoy_integration import send_buffer_group_to_pochtoy

        group_photos = PhotoBuffer.objects.filter(group_id=group_id, processed=False).order_by('id')

        if not group_photos.exists():
            return JsonResponse({'error': 'Группа пуста'}, status=400)

        # Отправляем в Pochtoy
        result = send_buffer_group_to_pochtoy(group_photos)

        if result and result.get('success'):
            # НЕ помечаем как processed - можно отправлять и в Pochtoy и создавать карточку
            return JsonResponse(result)
        else:
            return JsonResponse(result or {'error': 'Unknown error'}, status=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_buffer(request):
    """Очистить весь буфер - удалить все несортированные фото и файлы."""
    try:
        photos = PhotoBuffer.objects.filter(processed=False)
        deleted_count = photos.count()
        files_deleted = 0

        # Удаляем физические файлы
        for photo in photos:
            try:
                if photo.image and os.path.exists(photo.image.path):
                    os.remove(photo.image.path)
                    files_deleted += 1
                    print(f"Deleted file: {photo.image.path}")
            except Exception as e:
                print(f"Error deleting file for photo {photo.id}: {e}")

        # Удаляем записи из БД
        photos.delete()

        print(f"Cleared buffer: {deleted_count} records, {files_deleted} files")

        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'files_deleted': files_deleted
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_card_by_correlation(request, correlation_id):
    """Удалить карточку товара и вернуть фото в буфер если были из буфера."""
    try:
        # Находим карточку по correlation_id
        card = PhotoBatch.objects.filter(correlation_id=correlation_id).first()

        if not card:
            return JsonResponse({'error': 'Card not found'}, status=404)

        # Считаем что удаляем
        photos_count = card.photos.count()
        barcodes_count = card.get_all_barcodes().count()

        # Проверяем есть ли соответствующие записи в PhotoBuffer
        # (если карточка была создана из буфера)
        buffer_photos_returned = 0
        for photo in card.photos.all():
            try:
                # Ищем в буфере по message_id или file_id (если есть в метаданных)
                buffer_photo = PhotoBuffer.objects.filter(
                    message_id=photo.id,  # Примерно, нужно уточнить логику
                    processed=True
                ).first()

                if buffer_photo:
                    # Возвращаем в буфер
                    buffer_photo.processed = False
                    buffer_photo.sent_to_bot = False
                    buffer_photo.group_id = None
                    buffer_photo.save()
                    buffer_photos_returned += 1
            except:
                pass

        # Удаляем физические файлы фото
        files_deleted = 0
        for photo in card.photos.all():
            try:
                if photo.image and os.path.exists(photo.image.path):
                    os.remove(photo.image.path)
                    files_deleted += 1
            except Exception as e:
                print(f"Error deleting photo file {photo.id}: {e}")

        # Удаляем из Pochtoy перед удалением карточки
        try:
            from ..pochtoy_integration import delete_from_pochtoy

            # Собираем все трекинги
            trackings = []
            trackings.extend(card.get_gg_labels())
            for bc in card.get_all_barcodes():
                if bc.data not in trackings:
                    trackings.append(bc.data)

            if trackings:
                pochtoy_result = delete_from_pochtoy(trackings)
                print(f"Pochtoy delete result: {pochtoy_result}")
        except Exception as e:
            print(f"Pochtoy delete error: {e}")
            # Не падаем если Pochtoy недоступен

        # Удаляем карточку (каскадом удалятся Photo и BarcodeResult)
        card.delete()

        print(f"Deleted card {correlation_id}: {photos_count} photos, {barcodes_count} barcodes, {files_deleted} files, {buffer_photos_returned} returned to buffer")

        return JsonResponse({
            'success': True,
            'correlation_id': correlation_id,
            'photos_deleted': photos_count,
            'barcodes_deleted': barcodes_count,
            'files_deleted': files_deleted,
            'returned_to_buffer': buffer_photos_returned
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_last_card(request):
    """Получить последнюю созданную карточку."""
    try:
        last_card = PhotoBatch.objects.order_by('-uploaded_at').first()

        if not last_card:
            return JsonResponse({'correlation_id': None})

        photos_count = last_card.photos.all().count()

        return JsonResponse({
            'correlation_id': last_card.correlation_id,
            'title': last_card.title,
            'photos_count': photos_count,
            'uploaded_at': last_card.uploaded_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_buffer_photo(request, photo_id):
    """Удалить одно фото из буфера."""
    try:
        photo = PhotoBuffer.objects.filter(id=photo_id).first()

        if not photo:
            return JsonResponse({'error': 'Photo not found'}, status=404)

        # Удаляем файл
        if photo.image and os.path.exists(photo.image.path):
            os.remove(photo.image.path)

        # Удаляем запись
        photo.delete()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
