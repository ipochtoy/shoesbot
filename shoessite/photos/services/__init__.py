"""
Services package для работы с внешними API и обработки данных.

Предоставляет унифицированные сервисы для:
- OpenAI API (генерация описаний, анализ фото)
- FASHN AI API (генерация моделей в одежде)
- eBay поиск (поиск цен и фото товаров)
- Обработка изображений (resize, rotate, download)
"""

# API Client
from .api_client import BaseAPIClient, retry_on_exception

# AI Service
from .ai_service import (
    OpenAIService,
    get_ai_service,
    # Функции для обратной совместимости
    generate_product_description,
    suggest_category,
    suggest_price,
    analyze_photos_with_vision,
    auto_fill_product_card,
    generate_from_instruction,
    search_product_with_openai,
    generate_product_summary,
)

# FASHN Service
from .fashn_service import (
    FashnService,
    get_fashn_service,
    # Функции для обратной совместимости
    generate_model_with_product,
    change_background,
)

# Search Service
from .search_service import (
    EbaySearchService,
    get_ebay_service,
    # Функции для обратной совместимости
    search_products_on_ebay,
    search_price_on_ebay,
)

# Image Service
from .image_service import (
    ImageService,
    get_image_service,
    # Функции для обратной совместимости
    download_image_from_url,
    load_image_from_url,
    resize_image,
)


__all__ = [
    # Classes
    'BaseAPIClient',
    'OpenAIService',
    'FashnService',
    'EbaySearchService',
    'ImageService',

    # Decorators
    'retry_on_exception',

    # Singleton getters
    'get_ai_service',
    'get_fashn_service',
    'get_ebay_service',
    'get_image_service',

    # AI functions (backward compatibility)
    'generate_product_description',
    'suggest_category',
    'suggest_price',
    'analyze_photos_with_vision',
    'auto_fill_product_card',
    'generate_from_instruction',
    'search_product_with_openai',
    'generate_product_summary',

    # FASHN functions (backward compatibility)
    'generate_model_with_product',
    'change_background',

    # Search functions (backward compatibility)
    'search_products_on_ebay',
    'search_price_on_ebay',

    # Image functions (backward compatibility)
    'download_image_from_url',
    'load_image_from_url',
    'resize_image',
]
