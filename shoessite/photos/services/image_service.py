"""
Сервис для обработки изображений.

Предоставляет функции для:
- Загрузки изображений по URL
- Изменения размера
- Поворота
- Конвертации форматов
- Оптимизации
"""
import logging
from typing import Optional, Tuple
from io import BytesIO

import requests
from PIL import Image


logger = logging.getLogger(__name__)


class ImageService:
    """Сервис для работы с изображениями."""

    def __init__(self, default_timeout: int = 30):
        """
        Args:
            default_timeout: Timeout для загрузки изображений
        """
        self.default_timeout = default_timeout

    def download_from_url(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Optional[bytes]:
        """
        Скачивает изображение по URL.

        Args:
            url: URL изображения
            timeout: Timeout для запроса (переопределяет default_timeout)

        Returns:
            Байты изображения или None при ошибке
        """
        timeout = timeout or self.default_timeout

        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"Downloaded image from {url} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"Failed to download image: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading image from {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {e}")
            return None

    def load_from_bytes(self, data: bytes) -> Optional[Image.Image]:
        """
        Загружает изображение из байтов.

        Args:
            data: Байты изображения

        Returns:
            PIL Image объект или None при ошибке
        """
        try:
            return Image.open(BytesIO(data))
        except Exception as e:
            logger.error(f"Error loading image from bytes: {e}")
            return None

    def load_from_url(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Optional[Image.Image]:
        """
        Загружает изображение по URL.

        Args:
            url: URL изображения
            timeout: Timeout для запроса

        Returns:
            PIL Image объект или None при ошибке
        """
        data = self.download_from_url(url, timeout)
        if data:
            return self.load_from_bytes(data)
        return None

    def resize(
        self,
        image: Image.Image,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        keep_aspect_ratio: bool = True
    ) -> Image.Image:
        """
        Изменяет размер изображения.

        Args:
            image: PIL Image объект
            max_width: Максимальная ширина
            max_height: Максимальная высота
            keep_aspect_ratio: Сохранять пропорции

        Returns:
            Измененное изображение
        """
        if not max_width and not max_height:
            return image

        width, height = image.size

        if keep_aspect_ratio:
            # Вычисляем новый размер сохраняя пропорции
            if max_width and max_height:
                # Fit to box
                ratio = min(max_width / width, max_height / height)
            elif max_width:
                ratio = max_width / width
            else:  # max_height
                ratio = max_height / height

            new_width = int(width * ratio)
            new_height = int(height * ratio)
        else:
            new_width = max_width or width
            new_height = max_height or height

        logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def rotate(
        self,
        image: Image.Image,
        angle: int,
        expand: bool = True
    ) -> Image.Image:
        """
        Поворачивает изображение.

        Args:
            image: PIL Image объект
            angle: Угол поворота в градусах (против часовой стрелки)
            expand: Расширить изображение чтобы вместить все содержимое

        Returns:
            Повернутое изображение
        """
        logger.debug(f"Rotating image by {angle} degrees")
        return image.rotate(angle, expand=expand)

    def convert_format(
        self,
        image: Image.Image,
        format: str = 'JPEG',
        **save_params
    ) -> bytes:
        """
        Конвертирует изображение в нужный формат.

        Args:
            image: PIL Image объект
            format: Формат (JPEG, PNG, WEBP, etc.)
            **save_params: Дополнительные параметры для save()

        Returns:
            Байты изображения в новом формате
        """
        buffer = BytesIO()

        # Если конвертируем в JPEG, убираем альфа канал
        if format.upper() in ('JPEG', 'JPG') and image.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Устанавливаем дефолтные параметры для JPEG
        if format.upper() in ('JPEG', 'JPG') and 'quality' not in save_params:
            save_params['quality'] = 85

        image.save(buffer, format=format, **save_params)
        logger.debug(f"Converted image to {format} ({len(buffer.getvalue())} bytes)")
        return buffer.getvalue()

    def optimize(
        self,
        image: Image.Image,
        max_size_kb: int = 500,
        format: str = 'JPEG',
        initial_quality: int = 85
    ) -> bytes:
        """
        Оптимизирует изображение до заданного размера.

        Args:
            image: PIL Image объект
            max_size_kb: Максимальный размер в килобайтах
            format: Формат изображения
            initial_quality: Начальное качество (для JPEG)

        Returns:
            Байты оптимизированного изображения
        """
        quality = initial_quality
        min_quality = 30

        while quality >= min_quality:
            data = self.convert_format(image, format=format, quality=quality)
            size_kb = len(data) / 1024

            if size_kb <= max_size_kb:
                logger.info(f"Optimized image to {size_kb:.1f}KB (quality={quality})")
                return data

            # Уменьшаем качество
            quality -= 5

        logger.warning(f"Could not optimize image below {max_size_kb}KB")
        return data

    def get_dimensions(self, image: Image.Image) -> Tuple[int, int]:
        """
        Возвращает размеры изображения.

        Args:
            image: PIL Image объект

        Returns:
            Кортеж (width, height)
        """
        return image.size

    def crop(
        self,
        image: Image.Image,
        left: int,
        top: int,
        right: int,
        bottom: int
    ) -> Image.Image:
        """
        Обрезает изображение.

        Args:
            image: PIL Image объект
            left: Левая граница
            top: Верхняя граница
            right: Правая граница
            bottom: Нижняя граница

        Returns:
            Обрезанное изображение
        """
        logger.debug(f"Cropping image to ({left}, {top}, {right}, {bottom})")
        return image.crop((left, top, right, bottom))


# Singleton instance
_default_service = None


def get_image_service() -> ImageService:
    """Возвращает singleton instance ImageService."""
    global _default_service
    if _default_service is None:
        _default_service = ImageService()
    return _default_service


# Функции-обертки для удобства
def download_image_from_url(url: str) -> Optional[bytes]:
    """
    Скачивает изображение по URL.

    Args:
        url: URL изображения

    Returns:
        Байты изображения или None
    """
    return get_image_service().download_from_url(url)


def load_image_from_url(url: str) -> Optional[Image.Image]:
    """
    Загружает PIL Image по URL.

    Args:
        url: URL изображения

    Returns:
        PIL Image объект или None
    """
    return get_image_service().load_from_url(url)


def resize_image(
    image: Image.Image,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> Image.Image:
    """
    Изменяет размер изображения сохраняя пропорции.

    Args:
        image: PIL Image объект
        max_width: Максимальная ширина
        max_height: Максимальная высота

    Returns:
        Измененное изображение
    """
    return get_image_service().resize(image, max_width, max_height)
