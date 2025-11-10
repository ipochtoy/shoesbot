"""
Photo management views - функции управления фотографиями.
"""
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from ..models import Photo
from ..utils.error_handlers import api_success, api_error, handle_exceptions
import json
import os
import logging
from io import BytesIO
from PIL import Image

logger = logging.getLogger('photos.views')


@csrf_exempt
@require_http_methods(["POST"])
@handle_exceptions
def set_main_photo(request, photo_id):
    """Установить фото как главное."""
    photo = get_object_or_404(Photo, id=photo_id)
    photo.is_main = True
    photo.save()

    logger.info(f"Photo {photo_id} set as main")
    return api_success(message='Фото установлено как главное')


@csrf_exempt
@require_http_methods(["POST"])
@handle_exceptions
def move_photo(request, photo_id):
    """Переместить фото вверх или вниз."""
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
        return api_error('Фото не найдено', status=400)

    # Определяем новый индекс
    if direction == 'up' and current_index > 0:
        new_index = current_index - 1
    elif direction == 'down' and current_index < len(photos) - 1:
        new_index = current_index + 1
    else:
        return api_error('Нельзя переместить в этом направлении', status=400)

    # Меняем местами порядок
    other_photo = photos[new_index]
    photo_order = photo.order
    other_order = other_photo.order

    photo.order = other_order
    other_photo.order = photo_order

    photo.save()
    other_photo.save()

    direction_text = 'вверх' if direction == 'up' else 'вниз'
    logger.info(f"Photo {photo_id} moved {direction}")
    return api_success(message=f'Фото перемещено {direction_text}')


@csrf_exempt
@require_http_methods(["POST"])
@handle_exceptions
def delete_photo(request, photo_id):
    """Удалить фото."""
    photo = get_object_or_404(Photo, id=photo_id)
    card_id = photo.batch.id

    # Удаляем изображение из файловой системы
    if photo.image:
        photo.image.delete(save=False)

    # Удаляем объект Photo (баркоды удалятся каскадно)
    photo.delete()

    logger.info(f"Photo {photo_id} deleted from card {card_id}")
    return api_success(message='Фото удалено')


@csrf_exempt
@require_http_methods(["POST"])
@handle_exceptions
def rotate_photo(request, photo_id):
    """Повернуть фото на 90 градусов влево или вправо."""
    photo = get_object_or_404(Photo, id=photo_id)

    if not photo.image:
        return api_error('Фото не найдено', status=400)

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
            logger.warning(f"Could not delete old image file: {e}")

    direction_text = 'влево' if direction == 'left' else 'вправо'
    logger.info(f"Photo {photo_id} rotated {direction}")
    return api_success({'photo_url': photo.image.url}, message=f'Фото повернуто {direction_text}')
