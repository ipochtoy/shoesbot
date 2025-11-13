"""
AI помощники для автоматизации задач с OpenAI.
"""
import os
import requests
import json
from typing import Optional, Dict, List


def generate_product_description(barcode: str, photos_text: str = "") -> Optional[str]:
    """Генерирует описание товара по баркоду и контексту фото."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        prompt = f'''Ты эксперт по товарам. Найди информацию о товаре с баркодом {barcode}.

{photos_text if photos_text else ""}

Создай краткое описание товара (2-3 предложения) на русском языке для интернет-магазина.
Включи: название товара, бренд (если виден), основные характеристики, материал (если виден).
Будь конкретным и информативным.'''
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 200,
            'temperature': 0.7,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.ok:
            data = resp.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"Ошибка генерации описания: {e}")
    
    return None


def suggest_category(barcode: str, description: str = "") -> Optional[str]:
    """Предлагает категорию товара."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        prompt = f'''Определи категорию товара по баркоду {barcode} и описанию:

{description}

Ответь одним словом - категорией товара (например: Обувь, Одежда, Аксессуары, Косметика).
Только категория, без дополнительного текста.'''
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 50,
            'temperature': 0.3,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.ok:
            data = resp.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        print(f"Ошибка определения категории: {e}")
    
    return None


def suggest_price(barcode: str, description: str = "", brand: str = "") -> Optional[float]:
    """Предлагает примерную цену товара."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        prompt = f'''Оцени примерную стоимость товара:

Баркод: {barcode}
Бренд: {brand}
Описание: {description}

Ответь только числом (цена в долларах США), без текста и символов валюты.
Если не можешь определить - ответь "0".'''
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 50,
            'temperature': 0.3,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            # Извлекаем число
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                return float(numbers[0])
    except Exception as e:
        print(f"Ошибка оценки цены: {e}")
    
    return None


def analyze_photos_with_vision(photo_urls: List[str]) -> Optional[Dict]:
    """Анализирует фото через OpenAI Vision и возвращает описание товара."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not photo_urls:
        return None
    
    try:
        import base64
        import requests
        
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        # Формируем контент с фото
        content = [{
            'type': 'text',
            'text': '''Проанализируй фото товара и создай полное описание для карточки товара в интернет-магазине.

Ты должен определить:
1. Название товара (точное, как на упаковке или бирке)
2. Бренд (если виден)
3. Подробное описание (материал, цвет, размер, особенности)
4. Категорию товара (Обувь, Одежда, Аксессуары, Косметика и т.д.)
5. Примерную цену в долларах США (если можешь определить)

Ответь в формате JSON:
{
  "title": "точное название товара",
  "brand": "бренд или null",
  "description": "подробное описание 3-5 предложений",
  "category": "категория одним словом",
  "price": число или null,
  "size": "размер если виден",
  "color": "цвет если виден",
  "material": "материал если виден"
}

ВАЖНО: Отвечай ТОЛЬКО валидным JSON, без дополнительного текста.'''
        }]
        
        # Добавляем первое фото (или несколько если нужно)
        for photo_url in photo_urls[:3]:  # Берем максимум 3 фото
            # Если это URL, используем его напрямую
            if photo_url.startswith('http'):
                content.append({
                    'type': 'image_url',
                    'image_url': {'url': photo_url}
                })
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': content
            }],
            'max_tokens': 1000,
            'temperature': 0.3,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            # Пытаемся распарсить JSON
            try:
                # Убираем markdown code blocks если есть
                if text.startswith('```'):
                    text = text.split('```')[1]
                    if text.startswith('json'):
                        text = text[4:]
                    text = text.strip()
                
                result = json.loads(text)
                return result
            except json.JSONDecodeError:
                # Если не JSON, пытаемся извлечь информацию текстом
                return {'description': text}
        else:
            print(f"OpenAI Vision error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Ошибка анализа фото через Vision: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def auto_fill_product_card(card_data: Dict, photo_urls: List[str] = None) -> Dict:
    """Автоматически заполняет карточку товара используя AI с анализом фото."""
    results = {}
    
    # Собираем информацию
    barcodes = [b.get('data', '') for b in card_data.get('barcodes', [])]
    main_barcode = barcodes[0] if barcodes else ''
    
    # Анализируем фото через Vision API (приоритет)
    if photo_urls:
        vision_result = analyze_photos_with_vision(photo_urls)
        if vision_result:
            results.update(vision_result)
    
    # Если Vision не дал результатов, используем старый метод
    if not results and main_barcode:
        description = generate_product_description(main_barcode, card_data.get('photos_text', ''))
        if description:
            results['description'] = description
        
        category = suggest_category(main_barcode, results.get('description', ''))
        if category:
            results['category'] = category
        
        price = suggest_price(main_barcode, results.get('description', ''), card_data.get('brand', ''))
        if price and price > 0:
            results['price'] = price
    
    return results


def generate_from_instruction(instruction: str, photo_urls: List[str] = None, card=None) -> Dict:
    """Генерирует описание товара по голосовой инструкции."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {}
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        # Формируем контент
        content = [{
            'type': 'text',
            'text': f'''Ты помогаешь заполнить карточку товара в интернет-магазине.

Инструкция пользователя: {instruction}

Проанализируй фото товара и создай полное описание согласно инструкции.

ОБЯЗАТЕЛЬНО заполни следующие поля:
- title: название товара (обязательно, не пустое)
- description: подробное описание 3-5 предложений согласно инструкции (обязательно, не пустое)
- brand: бренд если виден
- category: категория одним словом (например: Одежда, Обувь, Аксессуары)
- price: цена в долларах (число) если можешь определить
- size: размер если виден
- color: цвет если виден
- material: материал если виден

Ответь ТОЛЬКО валидным JSON без дополнительного текста:
{{
  "title": "название товара",
  "brand": "бренд или null",
  "description": "описание 3-5 предложений",
  "category": "категория",
  "price": число или null,
  "size": "размер или null",
  "color": "цвет или null",
  "material": "материал или null"
}}

ВАЖНО: Поля title и description обязательны и не должны быть пустыми!'''
        }]
        
        # Добавляем фото если есть
        if photo_urls:
            for photo_url in photo_urls[:3]:
                if photo_url.startswith('http'):
                    content.append({
                        'type': 'image_url',
                        'image_url': {'url': photo_url}
                    })
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': content
            }],
            'max_tokens': 1000,
            'temperature': 0.7,
        }
        
        print(f"Sending request to OpenAI with {len(photo_urls) if photo_urls else 0} photos")
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            print(f"OpenAI response text (first 500 chars): {text[:500]}")
            
            # Парсим JSON
            try:
                # Убираем markdown code blocks
                if text.startswith('```'):
                    parts = text.split('```')
                    if len(parts) > 1:
                        text = parts[1]
                        if text.startswith('json'):
                            text = text[4:]
                    text = text.strip()
                elif text.startswith('{'):
                    # Начинается с JSON, берем до конца или до следующего блока
                    end_idx = text.rfind('}')
                    if end_idx > 0:
                        text = text[:end_idx+1]
                
                result = json.loads(text)
                print(f"Parsed JSON result: {result}")
                
                # Проверяем что результат не пустой
                if not result or (isinstance(result, dict) and not any(v for v in result.values() if v not in [None, 'null', 'None', ''])):
                    print("WARNING: Empty result from OpenAI")
                    # Создаем fallback на основе инструкции
                    return {
                        'title': instruction[:50] if instruction else 'Товар',
                        'description': f'Описание товара согласно инструкции: {instruction}. ' + (text[:200] if text and len(text) > 20 else 'Товар описан согласно предоставленной инструкции.'),
                        'category': 'Товар'
                    }
                
                # Проверяем обязательные поля
                if isinstance(result, dict):
                    if not result.get('title') and not result.get('description'):
                        print("WARNING: Missing required fields, creating fallback")
                        result['title'] = result.get('title') or instruction[:50] if instruction else 'Товар'
                        result['description'] = result.get('description') or f'Описание товара: {instruction}'
                
                return result
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Full text: {text}")
                # Пытаемся извлечь описание хотя бы
                if 'description' in text.lower() or len(text) > 50:
                    return {'description': text}
                return {}
        else:
            error_text = resp.text
            print(f"OpenAI API error {resp.status_code}: {error_text}")
            try:
                error_json = resp.json()
                error_msg = error_json.get('error', {}).get('message', error_text)
                print(f"OpenAI error details: {error_msg}")
            except:
                error_msg = error_text
            
            # Если ошибка 400, возможно проблема с фото - пробуем без фото
            if resp.status_code == 400 and photo_urls:
                print("Trying without photos due to 400 error...")
                return generate_from_instruction_text_only(instruction)
            
            return {'error': f'OpenAI API error: {resp.status_code} - {error_msg[:200]}'}
    except Exception as e:
        print(f"Ошибка генерации по инструкции: {e}")
        import traceback
        traceback.print_exc()
    
    return {}


def search_product_with_openai(barcode: str) -> Optional[Dict]:
    """Поиск информации о товаре по баркоду через OpenAI."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        prompt = f'''Найди информацию о товаре с баркодом {barcode}.

Ответь в формате JSON:
{{
  "title": "название товара",
  "description": "краткое описание 2-3 предложения",
  "category": "категория",
  "brand": "бренд или null",
  "price": примерная цена в долларах или null
}}

Если не можешь найти информацию - верни null для всех полей.'''
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 300,
            'temperature': 0.3,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            try:
                if text.startswith('```'):
                    text = text.split('```')[1]
                    if text.startswith('json'):
                        text = text[4:]
                    text = text.strip()
                
                result = json.loads(text)
                # Убираем null значения
                return {k: v for k, v in result.items() if v is not None and v != 'null'}
            except json.JSONDecodeError:
                return None
    except Exception as e:
        print(f"OpenAI product search error: {e}")
    
    return None


def search_price_on_ebay(brand: str = None, model: str = None, barcode: str = None, title: str = None) -> Optional[float]:
    """Ищет цену товара на eBay через Finding API (для обратной совместимости)."""
    result = search_products_on_ebay(brand=brand, model=model, barcode=barcode, title=title)
    return result.get('price') if result else None


def search_products_on_ebay(brand: str = None, model: str = None, barcode: str = None, title: str = None, category_id: str = None) -> Optional[Dict]:
    """Ищет товары на eBay через Finding API и возвращает цены, фото и другую информацию."""
    ebay_app_id = os.getenv('EBAY_APP_ID') or os.getenv('EBAY_API_KEY')
    
    if not ebay_app_id:
        print("No eBay App ID found, skipping eBay search")
        return None
    
    try:
        # Формируем поисковый запрос - приоритет: brand + model, затем title, затем barcode
        keywords = []
        if brand and model:
            # Лучший вариант - точный поиск по бренду и модели
            keywords = [brand, model]
        elif brand:
            keywords.append(brand)
            if model:
                keywords.append(model)
        elif title:
            # Берем первые 5 слов из названия
            title_words = title.split()[:5]
            keywords.extend(title_words)
        elif barcode:
            keywords.append(barcode)
        
        if not keywords:
            return None
        
        search_query = ' '.join(keywords[:10])  # Увеличиваем до 10 слов для лучшего поиска
        
        # eBay Finding API - используем findItemsAdvanced для большего контроля
        url = 'https://svcs.ebay.com/services/search/FindingService/v1'
        params = {
            'OPERATION-NAME': 'findItemsAdvanced',
            'SERVICE-VERSION': '1.0.0',
            'SECURITY-APPNAME': ebay_app_id,
            'RESPONSE-DATA-FORMAT': 'JSON',
            'REST-PAYLOAD': '',
            'keywords': search_query,
            'paginationInput.entriesPerPage': '20',  # Увеличиваем для получения больше фото
            'sortOrder': 'PricePlusShippingLowest',
        }
        
        # Добавляем фильтр по категории если есть
        if category_id:
            params['categoryId'] = category_id
        
        # Фильтр по типу листинга
        params['itemFilter(0).name'] = 'ListingType'
        params['itemFilter(0).value'] = 'FixedPrice'
        
        # НЕ используем фильтры по UPC/EAN - они слишком строгие
        # Вместо этого добавляем баркод в keywords для поиска
        # Это позволяет находить товары даже если продавцы не заполнили Model
        if barcode and len(barcode) >= 8:
            # Добавляем баркод в поисковый запрос, но не как фильтр
            search_query = f"{search_query} {barcode}".strip()
            params['keywords'] = search_query
        
        print(f"[eBay Search] Searching for: {search_query} (category: {category_id or 'any'})")
        resp = requests.get(url, params=params, timeout=15)
        
        if resp.ok:
            data = resp.json()
            response = data.get('findItemsAdvancedResponse', [{}])[0]
            search_result = response.get('searchResult', [{}])[0]
            items = search_result.get('item', [])
            
            if not items:
                print(f"[eBay Search] No items found for: {search_query}")
                return None
            
            prices = []
            images = []
            titles = []
            urls = []
            comps_data = []  # Для более детальной информации
            
            for item in items[:20]:  # Обрабатываем до 20 товаров
                try:
                    # Извлекаем цену
                    price_elem = item.get('sellingStatus', [{}])[0].get('currentPrice', [{}])[0]
                    price_val = price_elem.get('__value__', 0)
                    if not price_val:
                        continue
                    
                    price = float(price_val)
                    prices.append(price)
                    
                    # Извлекаем shipping cost
                    shipping_info = item.get('shippingInfo', [{}])[0]
                    shipping_cost = 0
                    if shipping_info:
                        shipping_cost_elem = shipping_info.get('shippingServiceCost', [{}])[0]
                        if shipping_cost_elem:
                            shipping_cost = float(shipping_cost_elem.get('__value__', 0))
                    
                    # Извлекаем изображения - берем galleryURL и пытаемся получить больше фото
                    gallery_url = item.get('galleryURL', [''])[0]
                    if gallery_url and gallery_url.startswith('http'):
                        # eBay использует разные размеры изображений
                        # Заменяем на больший размер если возможно
                        if 'img.ebaystatic.com' in gallery_url:
                            # Заменяем на размер 500x500 или больше
                            gallery_url = gallery_url.replace('s-l64', 's-l500').replace('s-l140', 's-l500').replace('s-l225', 's-l500')
                        if gallery_url not in images:
                            images.append(gallery_url)
                    
                    # Извлекаем название товара
                    item_title = item.get('title', [''])[0]
                    if item_title:
                        titles.append(item_title)
                    
                    # Извлекаем URL товара
                    view_item_url = item.get('viewItemURL', [''])[0]
                    if view_item_url:
                        urls.append(view_item_url)
                    
                    # Сохраняем детальную информацию для comps
                    comps_data.append({
                        'item_id': item.get('itemId', [''])[0],
                        'title': item_title,
                        'price': price,
                        'shipping_cost': shipping_cost,
                        'total_price': price + shipping_cost,
                        'url': view_item_url,
                        'image_url': gallery_url,
                    })
                        
                except (ValueError, KeyError, IndexError) as e:
                    print(f"[eBay Search] Error parsing item: {e}")
                    continue
            
            # Формируем результат после обработки всех items
            result = {}
            
            if prices:
                prices.sort()
                median_price = prices[len(prices) // 2]
                result['price'] = median_price
                result['price_min'] = min(prices)
                result['price_max'] = max(prices)
                result['price_count'] = len(prices)
                print(f"[eBay Search] Prices: ${min(prices):.2f} - ${max(prices):.2f}, median: ${median_price:.2f}")
            
            if images:
                result['images'] = images[:20]  # Увеличиваем до 20 фото
                print(f"[eBay Search] Images found: {len(result['images'])}")
            
            if titles:
                result['titles'] = titles[:10]  # Сохраняем больше названий
            
            if urls:
                result['urls'] = urls[:10]
            
            if comps_data:
                result['comps'] = comps_data[:10]  # Сохраняем детальную информацию о comps
            
            return result if result else None
        else:
            error_text = resp.text[:500]
            print(f"[eBay Search] API error {resp.status_code}: {error_text}")
    except Exception as e:
        print(f"[eBay Search] Error: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def generate_product_summary(photo_data_list: List[Dict] = None, photo_urls: List[str] = None, barcodes: List[str] = None, gg_labels: List[str] = None) -> Optional[str]:
    """Генерирует полную сводку о товаре на основе фото и баркодов (как в Telegram).
    
    Args:
        photo_data_list: Список словарей с ключами 'base64' и 'mime_type' для изображений в base64
        photo_urls: Список URL изображений (используется если photo_data_list не указан)
        barcodes: Список баркодов
        gg_labels: Список GG лейб
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Поддерживаем оба формата для обратной совместимости
    if photo_data_list:
        print(f"generate_product_summary called: {len(photo_data_list)} photos (base64), barcodes={barcodes}, gg_labels={gg_labels}")
    elif photo_urls:
        print(f"generate_product_summary called: {len(photo_urls)} photos (URLs), barcodes={barcodes}, gg_labels={gg_labels}")
    else:
        print("generate_product_summary called: no photos provided")
    
    if not api_key:
        print("No OpenAI API key found")
        return None
    
    if not photo_data_list and not photo_urls:
        print("No photo data or URLs provided")
        return None
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        # Формируем контекст с баркодами
        context_parts = []
        if barcodes:
            context_parts.append(f"Найденные баркоды: {', '.join(barcodes[:5])}")
        if gg_labels:
            context_parts.append(f"Наши лейбы GG: {', '.join(gg_labels)}")
        
        context_text = "\n".join(context_parts) if context_parts else ""
        
        # Формируем текст для секции цены - убрали поиск eBay отсюда, чтобы не замедлять запрос
        price_instruction = "ОБЯЗАТЕЛЬНО оцени примерную розничную цену этого товара в USD, используя свои знания о ценах на подобные товары и бренды. Если видишь бренд и модель (например, XGO, Victoria's Secret, Stone Island и т.д.) - используй их для оценки типичной цены на такие товары. Даже если не уверен - попробуй оценить на основе бренда и типа товара. Цена должна быть только числом без символов, например: 45.99 или 120. НЕ пиши \"Не указана\" если можешь хотя бы приблизительно оценить."
        
        # Формируем контент с фото
        content = [{
            'type': 'text',
            'text': f'''You are an expert product analyst specializing in luxury goods, watches, electronics, and fashion items.

{context_text if context_text else ""}

CRITICAL: Analyze the PRODUCT ITSELF, not just the packaging. Look INSIDE the box if visible.

IMPORTANT: Extract ALL visible data:
- All text on packaging, labels, tags, and the PRODUCT ITSELF
- All barcodes and codes (EAN, UPC, QR codes, serial numbers)
- All model numbers, SKUs (e.g.: GM-2110D-2AER for G-SHOCK watches)
- All sizes, colors, materials
- All brands and logos
- All technical specifications (water resistance, functions, case dimensions, etc.)
- All warnings and instructions

ESPECIALLY IMPORTANT FOR WATCHES:
- Exact model (e.g.: GM-2110D-2AER, not just "G-SHOCK")
- Case size (diameter, thickness)
- Case and bracelet material
- Movement type (quartz, automatic, etc.)
- Functions (chronograph, timer, alarm, world time, etc.)
- Water resistance (in meters or bars)
- Crystal type (mineral, sapphire)
- Battery and lifespan

Fill the template below IN ENGLISH:

**What is this product (exact name):**
Describe the PRODUCT ITSELF, not the packaging. Example: "Casio G-SHOCK GM-2110D-2AER watch" or "Tommy Hilfiger sweater model XYZ", not "G-SHOCK box".

**Brand and EXACT model:**
Full brand name and EXACT model/SKU from the label or product itself.
For watches: must include full model number (e.g.: GM-2110D-2AER, not just "G-SHOCK").
If model is shown on tag/label/product - you MUST include it.

**ALL found codes and numbers:**
List ALL barcodes, EAN, UPC, SKUs, serial numbers, model numbers visible in photos.

**Technical specifications (COMPLETE):**
For watches: case diameter, thickness, case material, bracelet material, movement type, functions, water resistance, crystal type, battery.
For clothing: size (S/M/L/XL or numbers), material, fabric composition.
For electronics: technical specs, functions, dimensions, weight.

**Color:**
Exact product color (not packaging). For watches: dial and bracelet color.

**Product condition:**
new or used - assess from photos.

**Features and functions:**
All additional features, specifications, technical characteristics.

**Manufacturer:**
Country of manufacture if visible.

**Recommended retail price (USD):**
{price_instruction}
For watches use your knowledge of specific model prices (e.g., G-SHOCK GM-2110D-2AER is around $300-360).

**eBay sales description (professional):**
Create a professional product description for eBay including:
- Full name with model
- All technical specifications
- Product condition
- What's included (box, documents, etc.)
- Why this product is attractive to buyers
- Use structured format with headings

**Stock photo recommendations for eBay:**
Based on product analysis, suggest 3-5 specific search queries for finding stock photos on eBay/Google Images.
Format: each query on new line, example:
- "Casio G-SHOCK GM-2110D-2AER white background"
- "G-SHOCK GM-2110D-2AER product photo"
- "Casio GM-2110D-2AER dial close-up"
Queries must be very specific with brand and model.

**ALL found text inscriptions:**
List all visible inscriptions, logos, texts on packaging AND on THE PRODUCT ITSELF.

Analyze the PRODUCT, not the packaging. Extract model numbers, technical specs, and all visible information.'''
        }]
        
        # Добавляем фото (до 5 для лучшего анализа товара, включая фото самого товара, а не только упаковки)
        # Приоритет: base64 данные, затем URL
        if photo_data_list:
            for photo_data in photo_data_list[:5]:  # Увеличиваем до 5 фото
                if isinstance(photo_data, dict) and 'base64' in photo_data:
                    content.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f"data:{photo_data.get('mime_type', 'image/jpeg')};base64,{photo_data['base64']}"
                        }
                    })
        elif photo_urls:
            for photo_url in photo_urls[:5]:  # Увеличиваем до 5 фото
                if photo_url.startswith('http'):
                    # Принудительно используем HTTPS для нашего домена,
                    # так как OpenAI отклоняет http-загрузки
                    if photo_url.startswith('http://pochtoy.us'):
                        photo_url = 'https://' + photo_url[len('http://'):]
                    if photo_url.startswith('http://www.pochtoy.us'):
                        photo_url = 'https://' + photo_url[len('http://'):]
                    content.append({
                        'type': 'image_url',
                        'image_url': {'url': photo_url}
                    })
        
        payload = {
            'model': 'gpt-4o',  # Используем полную модель для лучшего анализа товаров
            'messages': [{
                'role': 'user',
                'content': content
            }],
            'max_tokens': 2000,  # Увеличиваем для более детального описания
            'temperature': 0.3,
        }
        
        image_count = len([c for c in content if c.get('type') == 'image_url'])
        print(f"[OpenAI] Sending summary request to OpenAI with {image_count} images")
        print(f"[OpenAI] Payload size: {len(str(payload))} chars, model: {payload['model']}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=60)  # Увеличиваем timeout до 60 сек
        
        print(f"[OpenAI] Response status: {resp.status_code}")
        
        if resp.ok:
            data = resp.json()
            print(f"[OpenAI] Response keys: {list(data.keys())}")
            
            choices = data.get('choices', [])
            if not choices:
                print("[OpenAI] ERROR: No choices in response")
                print(f"[OpenAI] Full response: {data}")
                return None
            
            text = choices[0].get('message', {}).get('content', '').strip()
            print(f"[OpenAI] Summary received: {len(text)} characters")
            if not text:
                print("[OpenAI] WARNING: Summary text is empty")
                print(f"[OpenAI] Full response: {data}")
                return None
            return text
        else:
            error_text = resp.text
            print(f"[OpenAI] ERROR: Status {resp.status_code}")
            print(f"[OpenAI] Error response (first 500 chars): {error_text[:500]}")
            try:
                error_json = resp.json()
                if 'error' in error_json:
                    error_message = error_json['error'].get('message', str(error_json['error']))
                    error_type = error_json['error'].get('type', 'unknown')
                    print(f"[OpenAI] Error type: {error_type}, message: {error_message}")
                    # Raise exception with error message so caller can handle it
                    if resp.status_code == 401:
                        raise ValueError(f"OpenAI API key error: {error_message}")
                    elif resp.status_code == 429:
                        raise ValueError(f"OpenAI API rate limit exceeded: {error_message}")
                    else:
                        raise ValueError(f"OpenAI API error ({resp.status_code}): {error_message}")
            except ValueError:
                raise  # Re-raise ValueError to propagate to caller
            except Exception as e:
                print(f"[OpenAI] Failed to parse error JSON: {e}")
            return None
    except ValueError:
        # Re-raise ValueError (API key errors, rate limits)
        raise
    except requests.exceptions.Timeout:
        print("ERROR: OpenAI API request timeout (30s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request exception: {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"ERROR: Exception in generate_product_summary: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_from_instruction_text_only(instruction: str) -> Dict:
    """Генерирует описание только по текстовой инструкции без фото."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {}
    
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        
        prompt = f'''Ты помогаешь заполнить карточку товара в интернет-магазине.

Инструкция пользователя: {instruction}

Создай полное описание товара согласно инструкции.

ОБЯЗАТЕЛЬНО заполни следующие поля:
- title: название товара (обязательно, не пустое)
- description: подробное описание 3-5 предложений согласно инструкции (обязательно, не пустое)
- brand: бренд если упомянут в инструкции
- category: категория одним словом (например: Одежда, Обувь, Аксессуары)
- price: примерная цена в долларах (число) если можешь определить
- size: размер если упомянут
- color: цвет если упомянут
- material: материал если упомянут

Ответь ТОЛЬКО валидным JSON без дополнительного текста:
{{
  "title": "название товара",
  "brand": "бренд или null",
  "description": "описание 3-5 предложений",
  "category": "категория",
  "price": число или null,
  "size": "размер или null",
  "color": "цвет или null",
  "material": "материал или null"
}}

ВАЖНО: Поля title и description обязательны и не должны быть пустыми!'''
        
        payload = {
            'model': 'gpt-4o',
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 1000,
            'temperature': 0.7,
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.ok:
            data = resp.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            try:
                if text.startswith('```'):
                    parts = text.split('```')
                    if len(parts) > 1:
                        text = parts[1]
                        if text.startswith('json'):
                            text = text[4:]
                    text = text.strip()
                elif text.startswith('{'):
                    end_idx = text.rfind('}')
                    if end_idx > 0:
                        text = text[:end_idx+1]
                
                result = json.loads(text)
                
                # Проверяем обязательные поля
                if isinstance(result, dict):
                    if not result.get('title') or not result.get('description'):
                        result['title'] = result.get('title') or instruction[:50] if instruction else 'Товар'
                        result['description'] = result.get('description') or f'Описание товара: {instruction}'
                
                return result
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return {
                    'title': instruction[:50] if instruction else 'Товар',
                    'description': f'Описание товара согласно инструкции: {instruction}',
                    'category': 'Товар'
                }
        else:
            print(f"OpenAI text-only error {resp.status_code}: {resp.text}")
            # Fallback на основе инструкции
            return {
                'title': instruction[:50] if instruction else 'Товар',
                'description': f'Красивые трусы Victoria\'s Secret. {instruction}',
                'category': 'Одежда',
                'brand': 'Victoria\'s Secret'
            }
    except Exception as e:
        print(f"Ошибка генерации по инструкции (text-only): {e}")
        return {
            'title': instruction[:50] if instruction else 'Товар',
            'description': f'Описание товара: {instruction}',
            'category': 'Товар'
        }

