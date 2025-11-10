"""
Enhance views - функции улучшения фото через FASHN AI.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from django.db.models import Max
from ..models import Photo
import json
import os
import uuid
import sys


@csrf_exempt
@require_http_methods(["POST"])
def enhance_photo(request, photo_id):
    """Обработать фото через FASHN AI (ghost mannequin или background change)."""
    import traceback

    # Логируем в файл сразу
    with open('/tmp/enhance_calls.log', 'a') as f:
        f.write(f"\n=== enhance_photo called: photo_id={photo_id} ===\n")

    print(f"\n{'='*70}", file=sys.stderr)
    print(f"🚀 enhance_photo called: photo_id={photo_id}", file=sys.stderr)
    print(f"{'='*70}\n", file=sys.stderr)
    sys.stderr.flush()

    try:
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
                from ..fashn_api import generate_model_with_product, download_image_from_url
                print("✅ FASHN modules imported", file=sys.stderr)
                sys.stderr.flush()

                # Публичный URL через cloudflared
                cloudflared_url = os.getenv('CLOUDFLARED_URL', 'https://safely-ssl-collected-menus.trycloudflare.com')
                product_url = f"{cloudflared_url}{photo.image.url}"
                print(f"📁 Product URL: {product_url}", file=sys.stderr)
                sys.stderr.flush()

                # Подробный промпт для точности и реализма
                prompt = "realistic e-commerce catalog photo, product exactly as shown with accurate colors and textures, remove any price tags, soft beige background"
                if photo.batch.title:
                    title_lower = photo.batch.title.lower()
                    if any(x in title_lower for x in ['pants', 'брюки', 'штаны']):
                        prompt = "realistic full body catalog photo, product exactly as is, accurate fabric texture, remove price tags, soft beige background"
                    elif any(x in title_lower for x in ['dress', 'платье']):
                        prompt = "realistic catalog photo, product exactly as shown, natural pose, accurate fabric, remove price tags, soft beige background"
                    elif any(x in title_lower for x in ['shirt', 'рубашка', 'sweater', 'свитер', 'blouse', 'блузка', 'футболка', 't-shirt']):
                        prompt = "realistic upper body catalog photo, product exactly as is, accurate colors and print, sleeves as shown, remove price tags, soft beige background"

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
            # Background Change через FASHN (вместо Photoroom)
            try:
                from ..fashn_api import change_background, download_image_from_url
                print("✅ FASHN Background Change", file=sys.stderr)
                sys.stderr.flush()

                # Публичный URL
                cloudflared_url = os.getenv('CLOUDFLARED_URL', 'https://safely-ssl-collected-menus.trycloudflare.com')
                product_url = f"{cloudflared_url}{photo.image.url}"

                # Реалистичный промпт для Background Change
                bg_prompt = "professional product photography, realistic studio background with soft beige gradient, natural lighting, subtle shadows, high quality commercial photo"

                print(f"📁 URL: {product_url}", file=sys.stderr)
                print(f"📋 Background: {bg_prompt}", file=sys.stderr)
                sys.stderr.flush()

                result_url = change_background(product_url, bg_prompt)

                if result_url:
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

        if not enhanced_image:
            print("❌ Enhancement failed")
            return JsonResponse({
                'success': False,
                'error': f'Не удалось обработать фото ({mode}). Проверь API ключи и логи сервера.'
            }, status=500)

        # Создаем НОВОЕ фото вместо замены
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

        # Записываем полный traceback в файл и stderr
        tb = traceback.format_exc()
        print(f"\n{'='*70}", file=sys.stderr)
        print(f"❌ EXCEPTION in enhance_photo for photo_id={photo_id}:", file=sys.stderr)
        print(tb, file=sys.stderr)
        print(f"{'='*70}\n", file=sys.stderr)
        sys.stderr.flush()

        # Также в файл
        try:
            with open('/tmp/enhance_error.log', 'a') as f:
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
