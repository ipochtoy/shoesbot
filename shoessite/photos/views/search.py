"""
Search views - функции поиска товаров, баркодов, стоковых фото.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from ..models import PhotoBatch, Photo, BarcodeResult
import os
import requests
from bs4 import BeautifulSoup


@csrf_exempt
@require_http_methods(["GET"])
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
            from ..ai_helpers import search_product_with_openai
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
            from ..ai_helpers import search_products_on_ebay
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
