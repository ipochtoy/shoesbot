from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods as require_methods
from .models import PhotoBatch, Photo, BarcodeResult, ProcessingTask
from django.db.models import Max
import json

try:
    from .ai_helpers import auto_fill_product_card
except ImportError:
    def auto_fill_product_card(data):
        return {}
import uuid
import base64
import requests
import os
from decimal import Decimal
import re
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image

# Загружаем переменные окружения из .env
try:
    from dotenv import load_dotenv
    # Путь к корню проекта (где находится .env)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Загружен .env из: {env_path}")
    else:
        print(f"⚠️ .env файл не найден: {env_path}")
except ImportError:
    print("⚠️ python-dotenv не установлен")
except Exception as e:
    print(f"⚠️ Ошибка загрузки .env: {e}")


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
        
        return JsonResponse({
            'success': True,
            'correlation_id': correlation_id,
            'photos_saved': len(photo_objects),
            'barcodes_saved': barcode_count,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        import re
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


@staff_member_required
def search_by_barcode(request):
    """Поиск информации о товаре по баркоду."""
    barcode = request.GET.get('barcode', '')
    card_id = request.GET.get('card_id', '')  # ID карточки для поиска фото
    
    if not barcode:
        return JsonResponse({'error': 'Barcode required'}, status=400)
    
    try:
        # Пробуем несколько источников
        results = {}
        
        # 1. Google Lens / Vision API web detection - используем фото из карточки
        lens_results = search_with_google_lens(barcode, card_id)
        if lens_results:
            results.update(lens_results)
        
        # 2. Google Images по баркоду
        if 'images' not in results or not results.get('images'):
            images = search_google_images(barcode)
            if images:
                if 'images' not in results:
                    results['images'] = []
                results['images'].extend(images)
        
        # 3. Поиск через Google Shopping / OpenAI / обычный поиск
        product_info = search_product_info(barcode)
        # Объединяем результаты, но не перезаписываем то что уже есть от Lens
        for key, value in product_info.items():
            if key not in results or not results.get(key):
                results[key] = value
        
        # 4. Поиск через Bing Images (резервный вариант)
        if 'images' not in results or len(results.get('images', [])) < 3:
            bing_images = search_bing_images(barcode)
            if bing_images:
                if 'images' not in results:
                    results['images'] = []
                results['images'].extend(bing_images[:3])
        
        return JsonResponse(results)
        
    except Exception as e:
        import traceback
        print(f"Search error: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def search_google_images(barcode):
    """Поиск изображений через Google Custom Search API."""
    api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
    
    if not api_key or not search_engine_id:
        # Fallback: используем простой веб-поиск
        return search_google_images_web(barcode)
    
    url = f'https://www.googleapis.com/customsearch/v1'
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': f'{barcode} product',
        'searchType': 'image',
        'num': 6,
        'safe': 'active',
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.ok:
            data = resp.json()
            images = []
            for item in data.get('items', [])[:6]:
                images.append(item.get('link', ''))
            return images
    except:
        pass
    
    return search_google_images_web(barcode)


def search_google_images_web(barcode):
    """Простой веб-поиск изображений (fallback)."""
    try:
        # Используем DuckDuckGo или простой поиск
        search_url = f'https://www.google.com/search?q={barcode}+product&tbm=isch'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            images = []
            # Простой парсинг - в реальности лучше использовать API
            for img in soup.find_all('img', limit=10):
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http') and 'google' not in src:
                    images.append(src)
                    if len(images) >= 6:
                        break
            return images
    except:
        pass
    return []


def search_with_google_lens(barcode, card_id=None):
    """Поиск товара через Google Lens (Vision API Web Detection)."""
    results = {}
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    
    if not api_key:
        return results
    
    try:
        from .models import PhotoBatch, Photo, BarcodeResult
        
        # Ищем фото с этим баркодом в текущей карточке (если указана)
        photo = None
        if card_id:
            try:
                batch = PhotoBatch.objects.get(id=card_id)
                # Ищем фото с этим баркодом в этой карточке
                barcode_results = BarcodeResult.objects.filter(
                    data=barcode,
                    photo__batch=batch
                ).select_related('photo').first()
                if barcode_results:
                    photo = barcode_results.photo
            except PhotoBatch.DoesNotExist:
                pass
        
        # Если не нашли в карточке, ищем вообще
        if not photo:
            barcode_results = BarcodeResult.objects.filter(data=barcode).select_related('photo').first()
            if barcode_results:
                photo = barcode_results.photo
        
        # Если нашли фото, используем Vision API Web Detection (как Google Lens)
        if photo and photo.image:
            print(f"Using Vision API Web Detection for photo {photo.id} with barcode {barcode}")
            vision_results = search_product_with_vision_api(photo.image.path)
            if vision_results:
                print(f"Vision API found: {vision_results}")
                results.update(vision_results)
        
        # Также пробуем поиск через Custom Search API с Google Lens подходом
        search_engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
        if search_engine_id:
            url = 'https://www.googleapis.com/customsearch/v1'
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': f'{barcode} product',
                'searchType': 'image',
                'num': 6,
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                data = resp.json()
                images = []
                for item in data.get('items', [])[:6]:
                    img_url = item.get('link', '')
                    if img_url:
                        images.append(img_url)
                if images:
                    if 'images' not in results:
                        results['images'] = []
                    results['images'].extend(images)
                    
                    # Пробуем извлечь информацию из заголовков результатов
                    for item in data.get('items', [])[:3]:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        if title and not results.get('title'):
                            # Пытаемся извлечь название товара
                            if ' - ' in title:
                                results['title'] = title.split(' - ')[0]
                            elif len(title) < 100:
                                results['title'] = title
                        if snippet and not results.get('description'):
                            results['description'] = snippet[:500]
    except Exception as e:
        print(f"Google Lens search error: {e}")
        import traceback
        traceback.print_exc()
    
    return results


def search_product_with_vision_api(image_path):
    """Использует Google Vision API Web Detection для поиска товара (как Google Lens)."""
    results = {}
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    
    if not api_key:
        return results
    
    try:
        import base64
        
        # Читаем изображение
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
        
        payload = {
            'requests': [{
                'image': {'content': img_b64},
                'features': [
                    {'type': 'WEB_DETECTION', 'maxResults': 10},
                    {'type': 'LABEL_DETECTION', 'maxResults': 10},
                ]
            }]
        }
        
        resp = requests.post(url, json=payload, timeout=20)
        if resp.ok:
            data = resp.json()
            if 'responses' in data and data['responses']:
                response = data['responses'][0]
                web_detection = response.get('webDetection', {})
                
                # Извлекаем похожие товары
                pages_with_matching_images = web_detection.get('pagesWithMatchingImages', [])
                if pages_with_matching_images:
                    # Берем первый результат
                    first_page = pages_with_matching_images[0]
                    page_title = first_page.get('pageTitle', '')
                    if page_title and not results.get('title'):
                        # Пытаемся извлечь название товара
                        if ' - ' in page_title:
                            results['title'] = page_title.split(' - ')[0]
                        elif len(page_title) < 150:
                            results['title'] = page_title
                
                # КРИТИЧНО: Берём fullMatchingImages (точные совпадения товара), а не visuallySimilar (упаковка)
                full_matching = web_detection.get('fullMatchingImages', [])
                pages_with_matching = web_detection.get('pagesWithMatchingImages', [])
                visually_similar = web_detection.get('visuallySimilarImages', [])
                
                image_urls = []
                
                # 1. Полные совпадения (приоритет) - это стоковые фото товара
                for img in full_matching[:15]:
                    url = img.get('url')
                    if url:
                        image_urls.append(url)
                
                # 2. Страницы с подходящими изображениями товара
                for page in pages_with_matching[:10]:
                    url = page.get('url')
                    if url:
                        image_urls.append(url)
                
                # 3. Визуально похожие (fallback, ограничено)
                for img in visually_similar[:5]:
                    url = img.get('url')
                    if url:
                        image_urls.append(url)
                
                if image_urls:
                    results['images'] = image_urls[:20]
                    print(f"Vision API found {len(image_urls)} images: full={len(full_matching)}, pages={len(pages_with_matching)}, similar={len(visually_similar)}")
                
                # Извлекаем метки
                labels = response.get('labelAnnotations', [])
                if labels:
                    # Ищем категорию среди меток
                    category_keywords = ['одежда', 'обувь', 'аксессуар', 'товар', 'product', 'clothing', 'shoe', 'accessory']
                    for label in labels[:5]:
                        desc = label.get('description', '').lower()
                        if any(keyword in desc for keyword in category_keywords):
                            if not results.get('category'):
                                results['category'] = label.get('description', '')
                            break
    except Exception as e:
        print(f"Vision API web detection error: {e}")
        import traceback
        traceback.print_exc()
    
    return results


def search_bing_images(barcode):
    """Поиск изображений через Bing."""
    try:
        # Простой веб-поиск
        search_url = f'https://www.bing.com/images/search?q={barcode}+product'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            images = []
            for img in soup.find_all('img', limit=6):
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http') and 'bing' not in src and 'data:' not in src:
                    images.append(src)
            return images[:6]
    except:
        pass
    return []


def search_product_info(barcode):
    """Поиск названия и описания товара по баркоду через Google Shopping и OpenAI."""
    title = None
    description = None
    category = None
    brand = None
    price = None
    
    # 1. Пробуем Google Shopping через Custom Search API
    try:
        api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
        search_engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
        
        if api_key and search_engine_id:
            url = 'https://www.googleapis.com/customsearch/v1'
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': f'{barcode} product shopping',
                'num': 5,
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                data = resp.json()
                items = data.get('items', [])
                if items:
                    # Берем первый результат
                    first_item = items[0]
                    title = first_item.get('title', '').split(' - ')[0]  # Убираем сайт из названия
                    snippet = first_item.get('snippet', '')
                    if snippet:
                        description = snippet[:500]
    except Exception as e:
        print(f"Google Shopping search error: {e}")
    
    # 2. Если не нашли, пробуем OpenAI
    if not title and 'OPENAI_API_KEY' in os.environ:
        try:
            from .ai_helpers import search_product_with_openai
            ai_result = search_product_with_openai(barcode)
            if ai_result:
                title = ai_result.get('title') or title
                description = ai_result.get('description') or description
                category = ai_result.get('category') or category
                brand = ai_result.get('brand') or brand
                price = ai_result.get('price') or price
        except Exception as e:
            print(f"OpenAI search error: {e}")
    
    # 3. Fallback: простой веб-поиск
    if not title:
        try:
            search_url = f'https://www.google.com/search?q={barcode}+product+name'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.ok:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Ищем название в заголовках
                for h3 in soup.find_all('h3', limit=5):
                    text = h3.get_text().strip()
                    if text and len(text) > 10 and len(text) < 200:
                        title = text
                        break
                
                # Ищем описание
                if not description:
                    for div in soup.find_all('div', class_=['BNeawe', 's3v9rd']):
                        text = div.get_text().strip()
                        if text and len(text) > 50:
                            description = text[:500]
                            break
        except Exception as e:
            print(f"Web search error: {e}")
    
    result = {}
    if title:
        result['title'] = title
    if description:
        result['description'] = description
    if category:
        result['category'] = category
    if brand:
        result['brand'] = brand
    if price:
        result['price'] = price
    
    return result


@staff_member_required
@require_http_methods(["POST"])
def reprocess_photo(request, photo_id):
    """Повторная обработка фото для поиска баркодов."""
    photo = get_object_or_404(Photo, id=photo_id)
    
    try:
        # Добавляем путь к shoesbot в sys.path
        import sys
        # Путь к корню проекта (где находится shoesbot)
        current_file = os.path.abspath(__file__)  # shoessite/photos/views.py
        project_root = os.path.abspath(os.path.join(current_file, '../../'))  # ~/Projects/shoesbot
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from PIL import Image
        import asyncio
        from io import BytesIO
        
        # Читаем изображение
        with photo.image.open('rb') as f:
            image_bytes = f.read()
            image = Image.open(BytesIO(image_bytes))
            image.load()
        
        # Пробуем импортировать декодеры
        import_error = None
        try:
            from shoesbot.pipeline import BarcodePipeline
            from shoesbot.decoders.gg_label_decoder import GGLabelDecoder
            from shoesbot.decoders.vision_decoder import VisionDecoder
            from shoesbot.decoders.zbar_decoder import ZBarDecoder
            from shoesbot.decoders.opencv_qr_decoder import OpenCvQrDecoder
            
            # Инициализируем декодеры
            decoders = [
                ZBarDecoder(),
                OpenCvQrDecoder(),
                VisionDecoder(),
                GGLabelDecoder(),
            ]
            
            pipeline = BarcodePipeline(decoders)
            
            # Запускаем обработку
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(pipeline.run_smart_parallel_debug(image))
            finally:
                loop.close()
            
            print(f"Pipeline results: {len(results)} codes found")
                
        except ImportError as e:
            import_error = str(e)
            print(f"Import error: {e}")
            # Если не можем импортировать декодеры, используем прямые вызовы API
            results = []
            # Пробуем Google Vision API напрямую
            print("Trying Google Vision API directly...")
            vision_results = process_with_google_vision_direct(image, image_bytes)
            print(f"Google Vision found: {len(vision_results)} codes")
            results.extend(vision_results)
            # Пробуем OpenAI Vision (если доступен)
            print("Trying OpenAI Vision...")
            openai_results = process_with_openai_vision(image, image_bytes)
            print(f"OpenAI Vision found: {len(openai_results)} codes")
            results.extend(openai_results)
        
        # Если результатов нет, пробуем API напрямую в любом случае
        if not results and not import_error:
            print("No results from pipeline, trying direct API calls...")
            vision_results = process_with_google_vision_direct(image, image_bytes)
            results.extend(vision_results)
            openai_results = process_with_openai_vision(image, image_bytes)
            results.extend(openai_results)
        
        # Сохраняем найденные баркоды
        barcodes_found = []
        existing_barcodes = set()
        
        # Получаем существующие баркоды для этого фото
        for existing in photo.barcodes.all():
            existing_barcodes.add((existing.symbology, existing.data))
        
        for result in results:
            if hasattr(result, 'symbology'):
                # Это объект Barcode
                key = (result.symbology, result.data)
                source = result.source
                symbology = result.symbology
                data = result.data
            else:
                # Это словарь
                key = (result.get('symbology', ''), result.get('data', ''))
                source = result.get('source', 'unknown')
                symbology = result.get('symbology', '')
                data = result.get('data', '')
            
            if key not in existing_barcodes and data:
                BarcodeResult.objects.create(
                    photo=photo,
                    symbology=symbology,
                    data=data,
                    source=source
                )
                barcodes_found.append(f"{symbology}: {data} ({source})")
                existing_barcodes.add(key)
        
        # Собираем информацию о том, что было использовано
        api_info = []
        if 'GOOGLE_VISION_API_KEY' in os.environ:
            api_info.append('Google Vision API: доступен')
        else:
            api_info.append('Google Vision API: ключ не найден')
        
        if 'OPENAI_API_KEY' in os.environ:
            api_info.append('OpenAI Vision: доступен')
        else:
            api_info.append('OpenAI Vision: ключ не найден')
        
        return JsonResponse({
            'success': True,
            'barcodes_found': len(barcodes_found),
            'barcodes': barcodes_found if barcodes_found else ['Новых кодов не найдено'],
            'total_results': len(results),
            'api_info': api_info,
            'debug_info': {
                'used_pipeline': 'decoders' if 'pipeline' in locals() else 'direct_api',
                'google_vision_called': 'GOOGLE_VISION_API_KEY' in os.environ,
                'openai_called': 'OPENAI_API_KEY' in os.environ,
            }
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }, status=500)


def process_with_google_vision_direct(image, image_bytes):
    """Прямой вызов Google Vision API для поиска GG кодов."""
    results = []
    api_key = os.getenv('GOOGLE_VISION_API_KEY')
    
    if not api_key:
        print("Google Vision API: ключ не найден в переменных окружения")
        return results
    
    print(f"Google Vision API: ключ найден (первые 10 символов: {api_key[:10]}...)")
    
    try:
        import base64
        import requests
        from PIL import Image, ImageEnhance
        from io import BytesIO
        
        # Предобработка изображения для лучшего OCR
        # Увеличиваем разрешение для лучшего распознавания
        proc_img = image
        target_size = 2000  # Увеличиваем до 2000px для лучшего качества
        if image.width < target_size:
            ratio = target_size / float(image.width)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            proc_img = image.resize(new_size, Image.LANCZOS)  # LANCZOS лучше для текста
            print(f"Изображение увеличено с {image.width}x{image.height} до {proc_img.width}x{proc_img.height}")
        
        # Увеличиваем контраст и резкость
        proc_img = ImageEnhance.Contrast(proc_img).enhance(1.5)  # Увеличили до 1.5
        proc_img = ImageEnhance.Sharpness(proc_img).enhance(1.2)  # Добавили резкость
        
        print(f"Изображение обработано: контраст +50%, резкость +20%")
        
        # Сохраняем обработанное изображение
        buf = BytesIO()
        proc_img.save(buf, format='PNG')
        proc_bytes = buf.getvalue()
        
        # Кодируем изображение
        img_b64 = base64.b64encode(proc_bytes).decode('utf-8')
        url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
        
        payload = {
            'requests': [{
                'image': {'content': img_b64},
                'features': [
                    {'type': 'TEXT_DETECTION', 'maxResults': 10},
                    {'type': 'DOCUMENT_TEXT_DETECTION', 'maxResults': 10},
                ],
                'imageContext': {
                    'languageHints': ['en', 'ru']
                }
            }]
        }
        
        print(f"Отправка запроса в Google Vision API...")
        resp = requests.post(url, json=payload, timeout=20)
        print(f"Google Vision API ответ: статус {resp.status_code}")
        
        if resp.ok:
            data = resp.json()
            if 'responses' in data and data['responses']:
                response = data['responses'][0]
                
                # Получаем весь текст
                text = response.get('fullTextAnnotation', {}).get('text', '')
                print(f"Google Vision распознал текст (длина: {len(text)} символов)")
                print(f"ПОЛНЫЙ ТЕКСТ:\n{text}")
                
                # Также проверяем отдельные слова из textAnnotations
                text_annotations = response.get('textAnnotations', [])
                all_text = text
                all_words = []
                if text_annotations:
                    # Первый элемент - весь текст, остальные - отдельные слова
                    for annotation in text_annotations[1:]:
                        word = annotation.get('description', '')
                        all_text += ' ' + word
                        all_words.append(word)
                
                print(f"Всего текста для поиска: {len(all_text)} символов")
                print(f"Отдельные слова (первые 20): {all_words[:20]}")
                
                # Ищем GG коды в тексте - максимально широкие паттерны
                import re
                patterns = [
                    # Базовые паттерны
                    r'GG[-.\s]?(\d{2,4})',  # GG747, GG-747, GG 747
                    r'\bG(\d{3,4})\b',  # G747 (без второй G)
                    r'Q(\d{3,4})',  # Q747
                    # Более гибкие паттерны
                    r'[GQ]{1,2}[-.\s]?(\d{2,4})',  # Любая комбинация G/Q
                    r'(\d{2,4})',  # Просто цифры (может быть частью GG)
                ]
                
                found_codes = set()
                
                # Сначала ищем точные совпадения GG747
                for word in all_words:
                    word_upper = word.upper().strip()
                    # Прямое совпадение GG747
                    if re.match(r'^GG\d{2,4}$', word_upper):
                        found_codes.add(word_upper)
                        results.append({
                            'symbology': 'CODE39',
                            'data': word_upper,
                            'source': 'google-vision-direct'
                        })
                    # Варианты с разделителями GG-747, GG 747
                    elif re.match(r'^GG[-.\s]?\d{2,4}$', word_upper):
                        clean_word = re.sub(r'[-.\s]', '', word_upper)
                        if clean_word not in found_codes:
                            found_codes.add(clean_word)
                            results.append({
                                'symbology': 'CODE39',
                                'data': clean_word,
                                'source': 'google-vision-direct'
                            })
                    # Q коды Q747
                    elif re.match(r'^Q\d{3,4}$', word_upper):
                        if word_upper not in found_codes:
                            found_codes.add(word_upper)
                            results.append({
                                'symbology': 'CODE39',
                                'data': word_upper,
                                'source': 'google-vision-direct'
                            })
                    # Ошибки OCR: OO вместо GG (часто Google путает O и G)
                    elif re.match(r'^OO\d{2,4}$', word_upper):
                        # Заменяем OO на GG
                        gg_code = 'GG' + word_upper[2:]
                        if gg_code not in found_codes:
                            found_codes.add(gg_code)
                            results.append({
                                'symbology': 'CODE39',
                                'data': gg_code,
                                'source': 'google-vision-direct-ocr-fix'
                            })
                    # 66 вместо GG (6 похож на G)
                    elif re.match(r'^66\d{2,4}$', word_upper):
                        gg_code = 'GG' + word_upper[2:]
                        if gg_code not in found_codes:
                            found_codes.add(gg_code)
                            results.append({
                                'symbology': 'CODE39',
                                'data': gg_code,
                                'source': 'google-vision-direct-ocr-fix'
                            })
                    # G6, 6G вместо GG
                    elif re.match(r'^[G6]{2}\d{2,4}$', word_upper):
                        gg_code = 'GG' + re.sub(r'^[G6]{2}', '', word_upper)
                        if gg_code not in found_codes:
                            found_codes.add(gg_code)
                            results.append({
                                'symbology': 'CODE39',
                                'data': gg_code,
                                'source': 'google-vision-direct-ocr-fix'
                            })
                
                # Затем ищем паттернами во всем тексте
                for pattern in patterns:
                    matches = re.findall(pattern, all_text, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            num = match[0] if match[0] else ''
                        else:
                            num = match
                        
                        if num and num.isdigit() and len(num) >= 2:
                            # Определяем формат
                            if 'GG' in pattern.upper() or 'G' in pattern.upper():
                                label = f'GG{num}'
                            elif 'Q' in pattern.upper():
                                label = f'Q{num}'
                            else:
                                # Если просто цифры, проверяем контекст
                                # Ищем GG/OO/66 рядом с этими цифрами (747)
                                context_pattern = r'(?:GG|OO|66|G6|6G|GQ|QG)[-.\s]?' + num
                                if re.search(context_pattern, all_text, re.IGNORECASE):
                                    # Определяем правильный префикс
                                    context_match = re.search(context_pattern, all_text, re.IGNORECASE)
                                    if context_match:
                                        prefix = context_match.group(0).upper().replace('-', '').replace('.', '').replace(' ', '')
                                        if prefix.startswith('OO') or prefix.startswith('66'):
                                            label = f'GG{num}'
                                        elif prefix.startswith('G6') or prefix.startswith('6G'):
                                            label = f'GG{num}'
                                        else:
                                            label = f'GG{num}'
                                    else:
                                        label = f'GG{num}'
                                else:
                                    # Если цифры 747 и рядом есть G или O - возможно это GG
                                    num_with_context = re.search(r'[GO6Q]{1,2}[-.\s]?' + num, all_text, re.IGNORECASE)
                                    if num_with_context:
                                        label = f'GG{num}'
                                    else:
                                        continue
                            
                            if label not in found_codes:
                                found_codes.add(label)
                                results.append({
                                    'symbology': 'CODE39',
                                    'data': label,
                                    'source': 'google-vision-direct'
                                })
                
                # Дополнительный поиск: ищем любые 3-4 цифры и проверяем есть ли рядом G/O
                three_digit_nums = re.findall(r'\b(\d{3,4})\b', all_text)
                for num in three_digit_nums:
                    if num in ['747', '752', '753', '754']:  # Типичные GG коды
                        # Проверяем есть ли G/O/6 рядом (в пределах 5 символов)
                        num_pos = all_text.find(num)
                        if num_pos > 0:
                            context = all_text[max(0, num_pos-5):num_pos+len(num)+5]
                            if re.search(r'[GO6]{1,2}', context, re.IGNORECASE):
                                label = f'GG{num}'
                                if label not in found_codes:
                                    found_codes.add(label)
                                    results.append({
                                        'symbology': 'CODE39',
                                        'data': label,
                                        'source': 'google-vision-direct-context'
                                    })
                
                print(f"Найдено кодов: {len(results)}")
                for r in results:
                    print(f"  - {r['data']} ({r['source']})")
        
        elif resp.status_code == 403:
            print("Google Vision API: Access denied. Check API key and permissions.")
        elif resp.status_code == 400:
            error_data = resp.json()
            print(f"Google Vision API error: {error_data}")
        
    except Exception as e:
        import traceback
        print(f"Google Vision error: {e}")
        print(traceback.format_exc())
    
    return results


def process_with_openai_vision(image, image_bytes):
    """Использование OpenAI Vision API для поиска GG кодов."""
    results = []
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return results
    
    try:
        import base64
        import requests
        
        # Кодируем изображение
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': '''Найди на этом изображении все коды:
1. GG лейбы (например GG747, GG752) - верни в формате Q747, Q752 (т.е. замени GG на Q)
2. Q коды (например Q747, Q752) - верни как есть
3. Любые другие баркоды и коды

ВАЖНО: Все найденные GG коды должны быть в формате Q (GG747 -> Q747).
Ответь ТОЛЬКО найденными кодами через запятую, без дополнительного текста.
Формат: Q747, Q752, или просто: Q747'''
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{img_b64}'
                        }
                    }
                ]
            }],
            'max_tokens': 150,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            print(f"OpenAI ответ: {text}")
            
            # Парсим ответ - ищем Q коды
            import re
            # Ищем все Q коды (Q747, Q-747, Q 747)
            codes = re.findall(r'\bQ[-.\s]?(\d{2,4})\b', text, re.IGNORECASE)
            
            for match in codes:
                num = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else ''
                if num and num.isdigit():
                    q_code = f'Q{num}'
                    if not any(r.get('data') == q_code for r in results):
                        results.append({
                            'symbology': 'CODE39',
                            'data': q_code,
                            'source': 'openai-vision'
                        })
            
            # Также ищем GG коды и конвертируем в Q
            gg_codes = re.findall(r'\bGG[-.\s]?(\d{2,4})\b', text, re.IGNORECASE)
            for match in gg_codes:
                num = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else ''
                if num and num.isdigit():
                    q_code = f'Q{num}'
                    if not any(r.get('data') == q_code for r in results):
                        results.append({
                            'symbology': 'CODE39',
                            'data': q_code,
                            'source': 'openai-vision'
                        })
            
            print(f"OpenAI нашел кодов: {len(results)}")
        
    except Exception as e:
        print(f"OpenAI Vision error: {e}")
    
    return results


@staff_member_required
@require_http_methods(["POST"])
def generate_summary_api(request, card_id):
    """API endpoint для генерации сводки о товаре."""
    card = get_object_or_404(PhotoBatch, id=card_id)
    
    try:
        print(f"=== generate_summary_api called for card_id={card_id} ===")
        
        # Получаем фото и конвертируем в base64
        photos = card.photos.all()
        print(f"Found {photos.count()} photos")
        photo_data_list = []
        for photo in photos:
            if photo.image:
                try:
                    # Читаем файл и конвертируем в base64
                    photo.image.open()
                    image_data = photo.image.read()
                    photo.image.close()
                    
                    import base64
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    # Определяем MIME тип по расширению
                    mime_type = 'image/jpeg'
                    if photo.image.name.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif photo.image.name.lower().endswith('.webp'):
                        mime_type = 'image/webp'
                    
                    photo_data_list.append({
                        'base64': base64_data,
                        'mime_type': mime_type
                    })
                    print(f"  Photo {photo.id}: converted to base64 ({len(base64_data)} chars)")
                except Exception as e:
                    print(f"  ERROR converting photo {photo.id} to base64: {e}")
                    continue
        
        if not photo_data_list:
            print("ERROR: No photo data generated")
            return JsonResponse({
                'success': False,
                'error': 'Нет фото для анализа. Убедись, что фото загружены.'
            }, status=400)
        
        # Получаем баркоды и GG лейбы
        all_barcodes = card.get_all_barcodes()
        barcodes_list = [b.data for b in all_barcodes[:5]]
        gg_labels = card.get_gg_labels()
        print(f"Barcodes: {barcodes_list}, GG labels: {gg_labels}")
        
        # Генерируем сводку
        from .ai_helpers import generate_product_summary
        print("Calling generate_product_summary...")
        summary = generate_product_summary(
            photo_data_list=photo_data_list,
            barcodes=barcodes_list,
            gg_labels=gg_labels
        )
        
        print(f"Summary result: {summary[:100] if summary else 'None'}...")
        
        if summary:
            # Сохраняем сводку в БД
            card.ai_summary = summary
            card.save()
            print(f"✅ AI summary saved to card {card_id}")
            return JsonResponse({
                'success': True,
                'summary': summary
            })
        else:
            print("ERROR: generate_product_summary returned None")
            return JsonResponse({
                'success': False,
                'error': 'Не удалось сгенерировать сводку. Проверь логи сервера и наличие OPENAI_API_KEY.'
            }, status=500)
            
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"EXCEPTION in generate_summary_api: {e}")
        print(error_traceback)
        return JsonResponse({
            'success': False,
            'error': f'Ошибка: {str(e)}',
            'traceback': error_traceback
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
def generate_from_instruction_api(request, card_id):
    """API endpoint для генерации описания по голосовой инструкции."""
    card = get_object_or_404(PhotoBatch, id=card_id)
    
    try:
        import json
        data = json.loads(request.body)
        instruction = data.get('instruction', '')
        
        if not instruction:
            return JsonResponse({'error': 'Instruction required'}, status=400)
        
        # Получаем фото для анализа
        photos = card.photos.all()
        photo_urls = []
        for photo in photos:
            if photo.image:
                request_scheme = request.scheme if hasattr(request, 'scheme') else 'http'
                request_host = request.get_host() if hasattr(request, 'get_host') else 'localhost:8000'
                photo_url = f"{request_scheme}://{request_host}{photo.image.url}"
                photo_urls.append(photo_url)
        
        # Вызываем OpenAI для генерации по инструкции
        from .ai_helpers import generate_from_instruction
        result = generate_from_instruction(instruction, photo_urls, card)
        
        print(f"Generated result for instruction '{instruction[:50]}...': {result}")
        
        if not result:
            return JsonResponse({
                'success': False,
                'error': 'Не удалось сгенерировать описание. Проверь логи сервера.'
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def search_stock_photos(query, photo_paths=None):
    """Поиск стоковых фото товара по запросу и фото товара."""
    images = []
    seen_urls = set()
    
    # 1. Google Vision API Web Detection (Google Lens) - используем фото товара
    if photo_paths:
        for photo_path in photo_paths[:2]:  # Берем первые 2 фото
            try:
                vision_results = search_product_with_vision_api(photo_path)
                if vision_results.get('images'):
                    for img_url in vision_results['images']:
                        if img_url and img_url.startswith('http') and img_url not in seen_urls:
                            images.append({
                                'url': img_url,
                                'thumbnail': img_url,
                                'title': vision_results.get('title', ''),
                                'source': 'google_lens'
                            })
                            seen_urls.add(img_url)
                            if len(images) >= 12:
                                break
            except Exception as e:
                print(f"Error in Google Vision search: {e}")
            
            if len(images) >= 12:
                break
    
    # 2. Google Custom Search API (если есть)
    api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
    
    if api_key and search_engine_id and len(images) < 12:
        # Формируем несколько вариантов запросов
        search_queries = [
            query,
            f'{query} product',
            f'{query} official',
            f'{query} brand',
        ]
        
        for search_query in search_queries:
            if len(images) >= 12:
                break
                
            url = 'https://www.googleapis.com/customsearch/v1'
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': search_query,
                'searchType': 'image',
                'num': 10,
                'safe': 'active',
                'imgSize': 'large',
                'imgType': 'photo',
            }
            
            try:
                resp = requests.get(url, params=params, timeout=10)
                if resp.ok:
                    data = resp.json()
                    for item in data.get('items', []):
                        img_url = item.get('link', '')
                        if img_url and img_url.startswith('http') and img_url not in seen_urls:
                            images.append({
                                'url': img_url,
                                'thumbnail': item.get('image', {}).get('thumbnailLink', img_url),
                                'title': item.get('title', ''),
                                'source': 'google'
                            })
                            seen_urls.add(img_url)
                            if len(images) >= 12:
                                break
            except Exception as e:
                print(f"Error searching Google Images: {e}")
    
    # 3. Прямой поиск через Google Images (если Custom Search не работает)
    if len(images) < 8:
        try:
            # Используем DuckDuckGo Image Search API (бесплатный)
            ddg_url = 'https://api.duckduckgo.com/'
            params = {
                'q': f'{query} product',
                'iax': 'images',
                'ia': 'images',
            }
            resp = requests.get(ddg_url, params=params, timeout=10)
            if resp.ok:
                # DuckDuckGo возвращает HTML, парсим его
                soup = BeautifulSoup(resp.text, 'html.parser')
                for img in soup.find_all('img', limit=10):
                    src = img.get('src')
                    if src and src.startswith('http') and src not in seen_urls:
                        images.append({
                            'url': src,
                            'thumbnail': src,
                            'title': img.get('alt', ''),
                            'source': 'duckduckgo'
                        })
                        seen_urls.add(src)
                        if len(images) >= 12:
                            break
        except Exception as e:
            print(f"Error searching DuckDuckGo: {e}")
    
    # 4. Bing Images (fallback)
    if len(images) < 8:
        try:
            import urllib.parse
            search_url = f'https://www.bing.com/images/search?q={urllib.parse.quote(query + " product")}&qft=+filterui:imagesize-large'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.ok:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Ищем изображения в data-src и src атрибутах
                for img in soup.find_all('img', limit=20):
                    src = img.get('data-src') or img.get('src')
                    if src and src.startswith('http') and 'bing.com' not in src and src not in seen_urls:
                        # Фильтруем маленькие иконки
                        if 'icon' not in src.lower() and 'logo' not in src.lower():
                            images.append({
                                'url': src,
                                'thumbnail': src,
                                'title': img.get('alt', ''),
                                'source': 'bing'
                            })
                            seen_urls.add(src)
                            if len(images) >= 12:
                                break
        except Exception as e:
            print(f"Error searching Bing Images: {e}")
    
    return images[:12]


@csrf_exempt
@require_http_methods(["GET"])
def search_stock_photos_api(request, card_id):
    """API для поиска стоковых фото товара."""
    print(f"\n{'='*70}")
    print(f"🚀 STOCK PHOTOS SEARCH STARTED for card_id={card_id}")
    print(f"{'='*70}\n")
    
    try:
        card = get_object_or_404(PhotoBatch, id=card_id)
        search_barcode = request.GET.get('barcode', None)
        barcodes = card.get_all_barcodes()
        
        print(f"📋 Card: title={card.title}, brand={card.brand}, barcodes={len(barcodes)}")
        
        # Шаг 1: Определяем товар через OpenAI Vision (анализ фото)
        product_description = None
        photo_paths = []
        
        for photo in card.photos.all()[:2]:
            if photo.image:
                try:
                    photo_path = photo.image.path
                    if os.path.exists(photo_path):
                        photo_paths.append(photo_path)
                except:
                    pass
        
        if photo_paths:
            try:
                import base64
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    print(f"🔍 Analyzing {len(photo_paths)} photos with OpenAI Vision...")
                    
                    with open(photo_paths[0], 'rb') as f:
                        img_bytes = f.read()
                        b64_img = base64.b64encode(img_bytes).decode('utf-8')
                    
                    vision_prompt = '''Определи товар на фото максимально точно для поиска стоковых фото.

Верни: "Бренд тип_товара цвет особенности"
Пример: "Stone Island crew neck sweater black logo patch"

КРИТИЧНО:
- Если Stone Island (компас) - ОБЯЗАТЕЛЬНО включи бренд
- НЕ упоминай упаковку/пакет/barcode - опиши САМ ТОВАР
- Фокус на продукте, а не на том, как он упакован'''
                    
                    resp = requests.post('https://api.openai.com/v1/chat/completions', 
                        json={
                            'model': 'gpt-4o',
                            'messages': [{
                                'role': 'user',
                                'content': [
                                    {'type': 'text', 'text': vision_prompt},
                                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64_img}'}}
                                ]
                            }],
                            'max_tokens': 80,
                            'temperature': 0.2
                        },
                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                        timeout=15
                    )
                    
                    if resp.ok:
                        product_description = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip().strip('"').strip("'")
                        print(f"✅ OpenAI Vision identified: '{product_description}'")
            except Exception as e:
                print(f"❌ Error in OpenAI Vision: {e}")
        
        # Шаг 2: Формируем поисковый запрос (убираем баркоды/цифры)
        query = product_description or card.title or (card.brand + ' product' if card.brand else 'product')
        
        # Очищаем от баркодов и упаковочных слов
        import re
        query = re.sub(r'\b\d{8,}\b', '', query)  # Убираем длинные числа
        query = re.sub(r'\b(packaged|packaging|package|plastic|bag|box|boxed|wrapped)\b', '', query, flags=re.IGNORECASE)
        query = ' '.join(query.split())  # Убираем лишние пробелы
        
        print(f"📝 Search query (cleaned): '{query}'")
        
        # Шаг 3: Ищем фото из разных источников
        all_images = []
        
        # 3.1. eBay (передаём результат Vision или card.title)
        print(f"\n🛒 Searching eBay...")
        try:
            from .ai_helpers import search_products_on_ebay
            ebay_result = search_products_on_ebay(
                brand=card.brand,
                title=query,  # Используем результат Vision
                barcode=search_barcode or (barcodes[0].data if barcodes else None)
            )
            if ebay_result and ebay_result.get('images'):
                for img_url in ebay_result['images']:
                    all_images.append({
                        'url': img_url,
                        'thumbnail': img_url,
                        'title': f"eBay ({ebay_result.get('price', 'N/A')} USD)",
                        'source': 'ebay'
                    })
                print(f"✅ eBay: {len(ebay_result['images'])} images")
            else:
                print(f"⚠️ eBay: no results")
        except Exception as e:
            print(f"❌ eBay error: {e}")
        
        # 3.2. Google Lens (Vision Web Detection) - ТОЛЬКО fullMatchingImages
        print(f"\n🔍 Searching Google Lens...")
        if photo_paths:
            try:
                vision_results = search_product_with_vision_api(photo_paths[0])
                if vision_results.get('images'):
                    for img_url in vision_results['images'][:10]:
                        all_images.append({
                            'url': img_url,
                            'thumbnail': img_url,
                            'title': vision_results.get('title', ''),
                            'source': 'google_lens'
                        })
                    print(f"✅ Google Lens: {len(vision_results['images'])} images")
                else:
                    print(f"⚠️ Google Lens: no results")
            except Exception as e:
                print(f"❌ Google Lens error: {e}")
        
        # 3.3. Google Custom Search
        print(f"\n🔎 Searching Google Custom Search...")
        api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
        cx = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
        
        if api_key and cx:
            try:
                resp = requests.get('https://www.googleapis.com/customsearch/v1', params={
                    'key': api_key,
                    'cx': cx,
                    'q': query,
                    'searchType': 'image',
                    'num': 10,
                    'safe': 'active',
                    'imgSize': 'large'
                }, timeout=10)
                
                print(f"📡 CSE response: {resp.status_code}")
                
                if resp.ok:
                    data = resp.json()
                    items = data.get('items', [])
                    print(f"✅ CSE: {len(items)} items")
                    for item in items:
                        all_images.append({
                            'url': item.get('link'),
                            'thumbnail': item.get('image', {}).get('thumbnailLink', item.get('link')),
                            'title': item.get('title', ''),
                            'source': 'google'
                        })
                else:
                    error_text = resp.text[:200]
                    print(f"❌ CSE error {resp.status_code}: {error_text}")
            except Exception as e:
                print(f"❌ CSE exception: {e}")
        else:
            print(f"⚠️ CSE: API key or CX missing")
        
        # Шаг 4: Фильтрация и дедупликация
        print(f"\n🧹 Filtering {len(all_images)} total images...")
        
        excluded_domains = [
            'instagram.com', 'facebook.com', 'fbsbx.com', 'linkedin.com',
            'media.licdn.com', 'tiktok.com', 'twitter.com', 'pinterest.com',
            'lookaside.instagram.com', 'lookaside.fbsbx.com'
        ]
        
        seen_urls = set()
        unique_images = []
        filtered_count = 0
        
        for img in all_images:
            url = img.get('url', '')
            if not url or url in seen_urls:
                continue
            
            # Фильтруем соцсети
            is_social = any(domain in url.lower() for domain in excluded_domains)
            if is_social:
                filtered_count += 1
                continue
            
            seen_urls.add(url)
            unique_images.append(img)
        
        # Подсчёт источников
        sources = {}
        for img in unique_images:
            src = img.get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1
        
        print(f"✅ Final: {len(unique_images)} images (filtered {filtered_count})")
        print(f"📊 Sources: {sources}")
        
        return JsonResponse({
            'success': True,
            'images': unique_images[:12],
            'query': query,
            'debug': {
                'total_found': len(all_images),
                'filtered_out': filtered_count,
                'final_count': len(unique_images),
                'sources': sources,
                'version': 'v4.0_simplified'
            }
        })
        
    except Exception as e:
        import traceback
        print(f"Error in search_stock_photos_api: {e}")
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
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
def set_main_photo(request, photo_id):
    """Установить фото как главное."""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
        photo.is_main = True
        photo.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Фото установлено как главное'
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
def move_photo(request, photo_id):
    """Переместить фото вверх или вниз."""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
        data = json.loads(request.body) if request.body else {}
        direction = data.get('direction', 'up')  # 'up' or 'down'
        
        # Получаем все фото из того же батча, отсортированные по порядку
        photos = list(Photo.objects.filter(batch=photo.batch).order_by('-is_main', 'order', 'uploaded_at'))
        
        # Находим текущий индекс
        current_index = None
        for i, p in enumerate(photos):
            if p.id == photo.id:
                current_index = i
                break
        
        if current_index is None:
            return JsonResponse({'success': False, 'error': 'Фото не найдено'}, status=400)
        
        # Определяем новый индекс
        if direction == 'up' and current_index > 0:
            new_index = current_index - 1
        elif direction == 'down' and current_index < len(photos) - 1:
            new_index = current_index + 1
        else:
            return JsonResponse({'success': False, 'error': 'Нельзя переместить в этом направлении'}, status=400)
        
        # Меняем местами порядок
        other_photo = photos[new_index]
        photo_order = photo.order
        other_order = other_photo.order
        
        photo.order = other_order
        other_photo.order = photo_order
        
        photo.save()
        other_photo.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Фото перемещено {direction == "up" and "вверх" or "вниз"}'
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
def delete_photo(request, photo_id):
    """Удалить фото."""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
        card_id = photo.batch.id
        
        # Удаляем изображение из файловой системы
        if photo.image:
            photo.image.delete(save=False)
        
        # Удаляем объект Photo (баркоды удалятся каскадно)
        photo.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Фото удалено'
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
@staff_member_required
@require_http_methods(["POST"])
def save_ai_summary(request, card_id):
    """Сохранить AI сводку для карточки."""
    try:
        card = get_object_or_404(PhotoBatch, id=card_id)
        data = json.loads(request.body)
        summary_text = data.get('summary', '').strip()
        
        card.ai_summary = summary_text
        card.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Сводка сохранена'
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
def enhance_photo_photoroom(request, photo_id):
    """Обработать фото через Photoroom API."""
    import traceback
    import sys
    
    # Логируем в файл сразу
    with open('/tmp/enhance_calls.log', 'a') as f:
        f.write(f"\n=== enhance_photo_photoroom called: photo_id={photo_id} ===\n")
    
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"🚀 enhance_photo_photoroom called: photo_id={photo_id}", file=sys.stderr)
    print(f"{'='*70}\n", file=sys.stderr)
    sys.stderr.flush()
    
    try:
        import sys
        print(f"✅ Step 1: Getting photo {photo_id}", file=sys.stderr)
        sys.stderr.flush()
        
        photo = get_object_or_404(Photo, id=photo_id)
        print(f"✅ Step 2: Photo found: {photo.id}, image: {photo.image.name if photo.image else 'None'}", file=sys.stderr)
        sys.stderr.flush()
        
        if not photo.image:
            print("❌ Photo image is None", file=sys.stderr)
            return JsonResponse({'success': False, 'error': 'Фото не найдено'}, status=400)
        
        # Получаем режим обработки
        print(f"✅ Step 3: Parsing request body", file=sys.stderr)
        sys.stderr.flush()
        
        data = json.loads(request.body) if request.body else {}
        mode = data.get('mode', 'ghost_mannequin')  # ghost_mannequin или product_beautifier
        print(f"✅ Step 4: Mode = {mode}", file=sys.stderr)
        sys.stderr.flush()
        
        # Обрабатываем фото
        enhanced_image = None
        
        if mode == 'ghost_mannequin':
            # FASHN AI - генерация модели в одежде
            try:
                from .fashn_api import generate_model_with_product, download_image_from_url
                print("✅ FASHN modules imported", file=sys.stderr)
                sys.stderr.flush()
                
                # Публичный URL через cloudflared
                cloudflared_url = os.getenv('CLOUDFLARED_URL', 'https://safely-ssl-collected-menus.trycloudflare.com')
                product_url = f"{cloudflared_url}{photo.image.url}"
                print(f"📁 Product URL: {product_url}", file=sys.stderr)
                sys.stderr.flush()
                
                # Определяем prompt - акцент на ТОЧНОЕ сохранение товара как есть
                prompt = "e-commerce catalog photo, product exactly as shown, no modifications, soft beige background"
                if photo.batch.title:
                    title_lower = photo.batch.title.lower()
                    if any(x in title_lower for x in ['pants', 'брюки', 'штаны']):
                        prompt = "full body catalog photo, product exactly as is, no styling changes, soft beige background"
                    elif any(x in title_lower for x in ['dress', 'платье']):
                        prompt = "catalog photo, product exactly as shown, natural pose, soft beige background"
                    elif any(x in title_lower for x in ['shirt', 'рубашка', 'sweater', 'свитер', 'blouse', 'блузка']):
                        prompt = "upper body catalog photo, sleeves as shown, no rolling up, product exactly as is, soft beige background"
                
                print(f"📋 Prompt: {prompt}", file=sys.stderr)
                sys.stderr.flush()
                
                # Генерируем модель (асинхронный процесс с polling)
                print("🚀 Starting FASHN generation...", file=sys.stderr)
                sys.stderr.flush()
                
                result_url = generate_model_with_product(
                    product_url,
                    prompt=prompt,
                    resolution='1k'  # Точная генерация для каталога
                )
                
                print(f"📥 FASHN result URL: {result_url}", file=sys.stderr)
                sys.stderr.flush()
                
                if result_url:
                    # Скачиваем результат
                    print(f"📥 Downloading from FASHN CDN...", file=sys.stderr)
                    sys.stderr.flush()
                    enhanced_image = download_image_from_url(result_url)
                    print(f"📦 Downloaded: {len(enhanced_image) if enhanced_image else 0} bytes", file=sys.stderr)
                    sys.stderr.flush()
                else:
                    print("❌ FASHN returned None", file=sys.stderr)
                    sys.stderr.flush()
                    
            except Exception as e:
                print(f"❌ FASHN exception: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                sys.stderr.flush()
        else:
            # Product Beautifier через Photoroom
            try:
                from .photoroom_api import enhance_product_photo
                
                image_path = photo.image.path
                print(f"📁 Image path: {image_path}", file=sys.stderr)
                sys.stderr.flush()
                
                enhanced_image = enhance_product_photo(image_path, mode=mode)
                print(f"📦 Enhanced image: {len(enhanced_image) if enhanced_image else 'None'} bytes", file=sys.stderr)
                sys.stderr.flush()
                
            except Exception as e:
                print(f"❌ Photoroom exception: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                sys.stderr.flush()
        
        if not enhanced_image:
            print("❌ Enhancement failed")
            return JsonResponse({
                'success': False,
                'error': f'Не удалось обработать фото ({mode}). Проверь API ключи и логи сервера.'
            }, status=500)
        
        # Создаем НОВОЕ фото вместо замены
        from django.db.models import Max
        
        # Определяем порядок для нового фото
        max_order = Photo.objects.filter(batch=photo.batch).aggregate(Max('order'))['order__max'] or 0
        
        # Создаем новое фото
        new_photo = Photo.objects.create(
            batch=photo.batch,
            file_id=f'enhanced_{mode}_{uuid.uuid4().hex[:8]}',
            message_id=0,
            order=max_order + 1,
        )
        
        # Определяем расширение файла
        file_ext = 'png' if mode == 'ghost_mannequin' else 'jpg'
        filename = f'{photo.batch.correlation_id}_enhanced_{new_photo.id}.{file_ext}'
        
        # Сохраняем обработанное изображение
        new_photo.image.save(filename, ContentFile(enhanced_image), save=True)
        
        mode_text = 'ghost mannequin' if mode == 'ghost_mannequin' else 'улучшено'
        return JsonResponse({
            'success': True,
            'photo_id': new_photo.id,
            'photo_url': new_photo.image.url,
            'message': f'Фото обработано ({mode_text})',
            'reload': True  # Перезагрузить страницу чтобы показать новое фото
        })
            
    except Exception as e:
        import traceback
        import sys
        
        # Записываем полный traceback в файл и stderr
        tb = traceback.format_exc()
        print(f"\n{'='*70}", file=sys.stderr)
        print(f"❌ EXCEPTION in enhance_photo_photoroom for photo_id={photo_id}:", file=sys.stderr)
        print(tb, file=sys.stderr)
        print(f"{'='*70}\n", file=sys.stderr)
        sys.stderr.flush()
        
        # Также в файл
        try:
            with open('/tmp/photoroom_error.log', 'a') as f:
                f.write(f"\n{'='*70}\n")
                f.write(f"Error at photo_id={photo_id}: {e}\n")
                f.write(tb)
                f.write(f"\n{'='*70}\n")
        except:
            pass
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': tb
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def rotate_photo(request, photo_id):
    """Повернуть фото на 90 градусов влево или вправо."""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
        
        if not photo.image:
            return JsonResponse({'success': False, 'error': 'Фото не найдено'}, status=400)
        
        # Получаем направление поворота из запроса
        data = json.loads(request.body) if request.body else {}
        direction = data.get('direction', 'right')  # По умолчанию вправо
        
        # Определяем угол поворота
        # left = против часовой стрелки = +90 градусов
        # right = по часовой стрелке = -90 градусов
        angle = 90 if direction == 'left' else -90
        
        # Читаем текущее изображение
        with photo.image.open('rb') as f:
            image_bytes = f.read()
        
        img = Image.open(BytesIO(image_bytes))
        
        # Конвертируем в RGB если нужно
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Поворачиваем на указанный угол
        rotated_img = img.rotate(angle, expand=True)
        
        # Сохраняем повернутое изображение
        output = BytesIO()
        rotated_img.save(output, format='JPEG', quality=90)
        output.seek(0)
        
        # Извлекаем только имя файла (без пути), чтобы избежать дублирования пути
        # photo.image.name содержит полный путь типа 'photos/2025/11/04/filename.jpg'
        # Django автоматически добавит upload_to, поэтому берем только имя файла
        filename = os.path.basename(photo.image.name)
        
        # Удаляем старое изображение и сохраняем новое
        old_image_path = photo.image.path if photo.image else None
        photo.image.save(filename, ContentFile(output.read()), save=True)
        
        # Удаляем старый файл, если он существует и отличается от нового
        if old_image_path and os.path.exists(old_image_path) and old_image_path != photo.image.path:
            try:
                os.remove(old_image_path)
            except Exception as e:
                print(f"Warning: Could not delete old image file: {e}")
        
        direction_text = 'влево' if direction == 'left' else 'вправо'
        return JsonResponse({
            'success': True,
            'photo_url': photo.image.url,
            'message': f'Фото повернуто {direction_text}'
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
