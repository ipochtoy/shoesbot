"""
AI помощники для автоматизации задач с OpenAI.

DEPRECATED: Этот модуль оставлен для обратной совместимости.
Новый код должен использовать photos.services напрямую.

Все функции теперь импортируются из photos.services.ai_service
"""
import warnings
from typing import Optional, Dict, List

# Импортируем все функции из новых сервисов
from .services.ai_service import (
    generate_product_description,
    suggest_category,
    suggest_price,
    analyze_photos_with_vision,
    auto_fill_product_card,
    generate_from_instruction,
    search_product_with_openai,
    generate_product_summary,
)

from .services.search_service import (
    search_products_on_ebay,
    search_price_on_ebay,
)


# Функция которая была в ai_helpers но не перенесена (fallback для generate_from_instruction)
def generate_from_instruction_text_only(instruction: str) -> Dict:
    """
    Генерирует описание только по текстовой инструкции без фото.

    Deprecated: Используйте services.ai_service.generate_from_instruction() без photo_urls
    """
    warnings.warn(
        "generate_from_instruction_text_only is deprecated. "
        "Use services.ai_service.generate_from_instruction() without photo_urls instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from .services import get_ai_service
    return get_ai_service().generate_from_instruction(instruction, photo_urls=None)


# Экспорт всех функций для обратной совместимости
__all__ = [
    'generate_product_description',
    'suggest_category',
    'suggest_price',
    'analyze_photos_with_vision',
    'auto_fill_product_card',
    'generate_from_instruction',
    'search_product_with_openai',
    'search_products_on_ebay',
    'search_price_on_ebay',
    'generate_product_summary',
    'generate_from_instruction_text_only',
]
