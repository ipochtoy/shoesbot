"""
FASHN AI API integration for Product to Model generation.

DEPRECATED: Этот модуль оставлен для обратной совместимости.
Новый код должен использовать photos.services напрямую.

Все функции теперь импортируются из photos.services.fashn_service
"""
import warnings
from typing import Optional

# Импортируем все функции из новых сервисов
from .services.fashn_service import (
    generate_model_with_product,
    change_background,
)

from .services.image_service import (
    download_image_from_url,
)


# Константы для обратной совместимости
import os
FASHN_API_KEY = os.getenv('FASHN_API_KEY')
FASHN_API_URL = 'https://api.fashn.ai/v1'


# Экспорт всех функций для обратной совместимости
__all__ = [
    'generate_model_with_product',
    'change_background',
    'download_image_from_url',
    'FASHN_API_KEY',
    'FASHN_API_URL',
]
