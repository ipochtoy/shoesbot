"""
Admin views - админские функции, управление задачами, карточками товаров.
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from ..models import ProcessingTask, Photo, BarcodeResult, PhotoBatch
from decimal import Decimal
import os
import base64
import requests
import re

try:
    from ..ai_helpers import auto_fill_product_card
except ImportError:
    def auto_fill_product_card(data, photo_urls=None):
        return {}


@staff_member_required
def process_task(request, task_id):
    """Process a task with external API."""
    task = get_object_or_404(ProcessingTask, id=task_id)

    if task.status != 'pending':
        return redirect('admin:photos_processingtask_change', task_id)

    task.status = 'processing'
    task.save()

    try:
        # Process based on API name
        if task.api_name == 'google-vision':
            result = process_google_vision(task.photo)
        elif task.api_name == 'azure-cv':
            result = process_azure_cv(task.photo)
        else:
            result = {'error': f'Unknown API: {task.api_name}'}

        task.response_data = result
        task.status = 'completed' if 'error' not in result else 'failed'
        if 'error' in result:
            task.error_message = result['error']
        task.completed_at = timezone.now()
        task.save()

    except Exception as e:
        task.status = 'failed'
        task.error_message = str(e)
        task.completed_at = timezone.now()
        task.save()

    return redirect('admin:photos_processingtask_change', task_id)


@staff_member_required
def product_card_detail(request, card_id):
    """Детальная страница карточки товара."""
    card = get_object_or_404(PhotoBatch, id=card_id)

    if request.method == 'POST':
        # Обновляем данные карточки
        card.title = request.POST.get('title', '')
        card.description = request.POST.get('description', '')
        price_str = request.POST.get('price', '')
        if price_str:
            try:
                card.price = Decimal(price_str)
            except:
                card.price = None
        else:
            card.price = None
        card.condition = request.POST.get('condition', '')
        card.category = request.POST.get('category', '')
        card.brand = request.POST.get('brand', '')
        card.size = request.POST.get('size', '')
        card.color = request.POST.get('color', '')
        card.sku = request.POST.get('sku', '')
        quantity_str = request.POST.get('quantity', '1')
        try:
            card.quantity = int(quantity_str) if quantity_str else 1
        except ValueError:
            card.quantity = 1
        card.save()
        return redirect('product_card_detail', card_id=card.id)

    # Получаем данные
    photos = card.photos.all()
    gg_labels = card.get_gg_labels()
    all_barcodes = card.get_all_barcodes()

    # Автозаполнение через AI (если есть OpenAI ключ) - всегда вызываем
    ai_suggestions = {}
    ai_summary = card.ai_summary if card.ai_summary else None

    if 'OPENAI_API_KEY' in os.environ:
        try:
            barcodes_data = [{'data': b.data, 'source': b.source} for b in all_barcodes[:3]]
            # Получаем URL фото для анализа
            photo_urls = []
            for photo in photos:
                if photo.image:
                    # Формируем полный URL
                    request_scheme = request.scheme if hasattr(request, 'scheme') else 'http'
                    request_host = request.get_host() if hasattr(request, 'get_host') else 'localhost:8000'
                    photo_url = f"{request_scheme}://{request_host}{photo.image.url}"
                    photo_urls.append(photo_url)
                    print(f"Photo URL: {photo_url}")

            ai_suggestions = auto_fill_product_card({
                'barcodes': barcodes_data,
                'brand': card.brand,
            }, photo_urls=photo_urls)
        except Exception as e:
            print(f"Ошибка AI автозаполнения: {e}")
            import traceback
            traceback.print_exc()

    return render(request, 'photos/product_card.html', {
        'card': card,
        'photos': photos,
        'gg_labels': gg_labels,
        'all_barcodes': all_barcodes,
        'ai_suggestions': ai_suggestions,
        'ai_summary': ai_summary,
    })


def process_google_vision(photo):
    """Process photo with Google Vision API and extract barcodes."""
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    if not api_key:
        return {'error': 'GOOGLE_VISION_API_KEY not set'}

    # Read image
    with photo.image.open('rb') as f:
        image_bytes = f.read()

    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'

    payload = {
        'requests': [{
            'image': {'content': img_b64},
            'features': [
                {'type': 'TEXT_DETECTION'},
                {'type': 'LABEL_DETECTION'},
            ]
        }]
    }

    resp = requests.post(url, json=payload, timeout=30)
    if not resp.ok:
        return {'error': f'API error: {resp.status_code}'}

    data = resp.json()

    # Extract text and find GG labels
    if 'responses' in data and data['responses']:
        response = data['responses'][0]
        text = response.get('fullTextAnnotation', {}).get('text', '')

        # Extract GG labels from text
        gg_pattern = re.compile(r'\b(GG[-.\s]?(\d+)|G(\d{4}))\b', re.IGNORECASE)
        matches = gg_pattern.findall(text)

        barcodes_found = []
        seen = set()
        for match in matches:
            if match[1]:  # GG pattern
                num = match[1]
                label = f'GG{num}'
            elif match[2]:  # G + 4 digits
                num = match[2]
                label = f'G{num}'
            else:
                continue

            if label not in seen:
                seen.add(label)
                # Save to BarcodeResult
                BarcodeResult.objects.get_or_create(
                    photo=photo,
                    symbology='GG',
                    data=label,
                    defaults={'source': 'google-vision-admin'}
                )
                barcodes_found.append(label)

        data['_extracted_barcodes'] = barcodes_found
        data['_text_preview'] = text[:500] if text else ''

    return data


def process_azure_cv(photo):
    """Process photo with Azure Computer Vision."""
    # TODO: Implement Azure CV
    return {'error': 'Azure CV not implemented yet'}
