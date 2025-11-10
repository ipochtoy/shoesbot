"""
AI views - функции работы с AI (генерация описаний, сводок).
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from ..models import PhotoBatch
import json
import base64


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
        from ..ai_helpers import generate_product_summary
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
        from ..ai_helpers import generate_from_instruction
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
