"""
Barcodes views - функции обработки и распознавания баркодов.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from ..models import Photo, BarcodeResult, PhotoBatch
import json
import os
import base64


@staff_member_required
@require_http_methods(["POST"])
def reprocess_photo(request, photo_id):
    """Повторная обработка фото для поиска баркодов."""
    photo = get_object_or_404(Photo, id=photo_id)

    try:
        # Добавляем путь к shoesbot в sys.path
        import sys
        # Путь к корню проекта (где находится shoesbot)
        current_file = os.path.abspath(__file__)  # shoessite/photos/views/barcodes.py
        project_root = os.path.abspath(os.path.join(current_file, '../../../'))
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
            from shoesbot.pipeline import DecoderPipeline
            from shoesbot.decoders.gg_label_decoder import GGLabelDecoder
            from shoesbot.decoders.vision_decoder import VisionDecoder
            from shoesbot.decoders.zbar_decoder import ZBarDecoder
            from shoesbot.decoders.cv_qr_decoder import OpenCvQrDecoder
            from shoesbot.decoders.openai_barcode_decoder import OpenAIBarcodeDecoder

            # Инициализируем декодеры (включая OpenAI для веб-интерфейса)
            decoders = [
                ZBarDecoder(),
                OpenCvQrDecoder(),
                VisionDecoder(),
                GGLabelDecoder(),
                OpenAIBarcodeDecoder(),  # Только для веб-интерфейса
            ]

            pipeline = DecoderPipeline(decoders)

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


@csrf_exempt
@require_http_methods(["POST"])
def add_barcode_manually(request, card_id):
    """Добавить баркод вручную."""
    try:
        card = get_object_or_404(PhotoBatch, id=card_id)
        data = json.loads(request.body)

        barcode_data = data.get('barcode', '').strip()
        symbology = data.get('symbology', 'EAN13')

        if not barcode_data:
            return JsonResponse({'success': False, 'error': 'Баркод не указан'}, status=400)

        # Создаем баркод на первом фото карточки
        first_photo = card.photos.first()
        if not first_photo:
            return JsonResponse({'success': False, 'error': 'Нет фото в карточке'}, status=400)

        # Проверяем что такого баркода еще нет
        existing = BarcodeResult.objects.filter(
            photo__batch=card,
            data=barcode_data,
            symbology=symbology
        ).exists()

        if existing:
            return JsonResponse({'success': False, 'error': 'Такой баркод уже существует'}, status=400)

        # Создаем баркод
        BarcodeResult.objects.create(
            photo=first_photo,
            symbology=symbology,
            data=barcode_data,
            source='manual'
        )

        return JsonResponse({
            'success': True,
            'message': 'Баркод добавлен'
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def process_with_google_vision_direct(image, image_bytes):
    """Прямой вызов Google Vision API для поиска GG кодов."""
    import re
    import requests
    from PIL import Image as PILImage, ImageEnhance
    from io import BytesIO

    results = []
    api_key = os.getenv('GOOGLE_VISION_API_KEY')

    if not api_key:
        print("Google Vision API: ключ не найден в переменных окружения")
        return results

    print(f"Google Vision API: ключ найден (первые 10 символов: {api_key[:10]}...)")

    try:
        # Предобработка изображения для лучшего OCR
        # Увеличиваем разрешение для лучшего распознавания
        proc_img = image
        target_size = 2000  # Увеличиваем до 2000px для лучшего качества
        if image.width < target_size:
            ratio = target_size / float(image.width)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            proc_img = image.resize(new_size, PILImage.LANCZOS)  # LANCZOS лучше для текста
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
                    # Ошибки OCR: OO вместо GG
                    elif re.match(r'^OO\d{2,4}$', word_upper):
                        gg_code = 'GG' + word_upper[2:]
                        if gg_code not in found_codes:
                            found_codes.add(gg_code)
                            results.append({
                                'symbology': 'CODE39',
                                'data': gg_code,
                                'source': 'google-vision-direct-ocr-fix'
                            })
                    # 66 вместо GG
                    elif re.match(r'^66\d{2,4}$', word_upper):
                        gg_code = 'GG' + word_upper[2:]
                        if gg_code not in found_codes:
                            found_codes.add(gg_code)
                            results.append({
                                'symbology': 'CODE39',
                                'data': gg_code,
                                'source': 'google-vision-direct-ocr-fix'
                            })

                print(f"Найдено кодов: {len(results)}")

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
    import re
    import requests

    results = []
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        return results

    try:
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
                        'text': """Найди на этом изображении все коды:
1. GG лейбы (например GG747, GG752) - верни в формате Q747, Q752 (т.е. замени GG на Q)
2. Q коды (например Q747, Q752) - верни как есть
3. Любые другие баркоды и коды

ВАЖНО: Все найденные GG коды должны быть в формате Q (GG747 -> Q747).
Ответь ТОЛЬКО найденными кодами через запятую, без дополнительного текста.
Формат: Q747, Q752, или просто: Q747"""
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
