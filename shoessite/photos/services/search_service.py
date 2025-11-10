"""
Сервис для поиска товаров по баркодам в различных источниках.

Поддерживаемые источники:
- eBay Finding API
- Google Search (планируется)
- Bing Search (планируется)
"""
import os
import logging
from typing import Optional, Dict, List, Any

from .api_client import BaseAPIClient


logger = logging.getLogger(__name__)


class EbaySearchService:
    """Сервис для поиска товаров на eBay."""

    def __init__(self, app_id: Optional[str] = None):
        """
        Args:
            app_id: eBay App ID (если None, берется из EBAY_APP_ID или EBAY_API_KEY env)
        """
        self.app_id = app_id or os.getenv('EBAY_APP_ID') or os.getenv('EBAY_API_KEY')
        if not self.app_id:
            logger.warning("eBay App ID not set")

        self.client = BaseAPIClient(
            base_url='https://svcs.ebay.com/services/search/FindingService/v1',
            timeout=10
        )

    def search_products(
        self,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        barcode: Optional[str] = None,
        title: Optional[str] = None,
        max_items: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Ищет товары на eBay через Finding API.

        Args:
            brand: Бренд товара
            model: Модель товара
            barcode: Баркод товара
            title: Название товара
            max_items: Максимальное количество результатов

        Returns:
            Словарь с ценами, фото и другой информацией или None
        """
        if not self.app_id:
            logger.warning("No eBay App ID, skipping eBay search")
            return None

        # Формируем поисковый запрос
        keywords = []
        if brand:
            keywords.append(brand)
        if model:
            keywords.append(model)
        if title:
            # Берем первые 3 слова из названия
            title_words = title.split()[:3]
            keywords.extend(title_words)
        if barcode:
            keywords.append(barcode)

        if not keywords:
            return None

        search_query = ' '.join(keywords[:5])  # Максимум 5 слов

        try:
            params = {
                'OPERATION-NAME': 'findItemsByKeywords',
                'SERVICE-VERSION': '1.0.0',
                'SECURITY-APPNAME': self.app_id,
                'RESPONSE-DATA-FORMAT': 'JSON',
                'REST-PAYLOAD': '',
                'keywords': search_query,
                'paginationInput.entriesPerPage': str(max_items),
                'itemFilter(0).name': 'ListingType',
                'itemFilter(0).value': 'FixedPrice',
                'sortOrder': 'PricePlusShippingLowest'
            }

            logger.info(f"Searching eBay for: {search_query}")

            response = self.client.get('', params=params)

            if not response.ok:
                logger.error(f"eBay API error: {response.status_code} - {response.text[:200]}")
                return None

            data = response.json()
            items = (
                data.get('findItemsByKeywordsResponse', [{}])[0]
                .get('searchResult', [{}])[0]
                .get('item', [])
            )

            if not items:
                return None

            # Собираем информацию
            prices = []
            images = []
            titles = []
            urls = []

            for item in items[:max_items]:
                try:
                    # Извлекаем цену
                    price_val = (
                        item.get('sellingStatus', [{}])[0]
                        .get('currentPrice', [{}])[0]
                        .get('__value__')
                    )
                    if price_val:
                        prices.append(float(price_val))

                    # Извлекаем изображения
                    gallery_url = item.get('galleryURL', [''])[0]
                    if gallery_url and gallery_url.startswith('http'):
                        # Заменяем на больший размер
                        if 'img.ebaystatic.com' in gallery_url:
                            gallery_url = gallery_url.replace('s-l64', 's-l225').replace('s-l140', 's-l225')
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

                except (ValueError, KeyError, IndexError) as e:
                    logger.warning(f"Error parsing eBay item: {e}")
                    continue

            # Формируем результат
            result = {}

            if prices:
                prices.sort()
                median_price = prices[len(prices) // 2]
                result['price'] = median_price
                result['price_min'] = min(prices)
                result['price_max'] = max(prices)
                result['price_count'] = len(prices)
                logger.info(
                    f"eBay prices found: ${min(prices):.2f} - ${max(prices):.2f}, "
                    f"median: ${median_price:.2f}"
                )

            if images:
                result['images'] = images[:12]  # Ограничиваем до 12 фото
                logger.info(f"eBay images found: {len(result['images'])}")

            if titles:
                result['titles'] = titles[:5]  # Сохраняем несколько названий

            if urls:
                result['urls'] = urls[:5]

            return result if result else None

        except Exception as e:
            logger.error(f"Error searching eBay: {e}", exc_info=True)
            return None

    def search_price(
        self,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        barcode: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[float]:
        """
        Ищет цену товара на eBay (для обратной совместимости).

        Args:
            brand: Бренд товара
            model: Модель товара
            barcode: Баркод товара
            title: Название товара

        Returns:
            Медианная цена или None
        """
        result = self.search_products(brand=brand, model=model, barcode=barcode, title=title)
        return result.get('price') if result else None


# Singleton instance
_default_ebay_service = None


def get_ebay_service() -> EbaySearchService:
    """Возвращает singleton instance EbaySearchService."""
    global _default_ebay_service
    if _default_ebay_service is None:
        _default_ebay_service = EbaySearchService()
    return _default_ebay_service


# Функции-обертки для обратной совместимости со старым API
def search_products_on_ebay(
    brand: str = None,
    model: str = None,
    barcode: str = None,
    title: str = None
) -> Optional[Dict]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ebay_service().search_products(brand=brand, model=model, barcode=barcode, title=title)


def search_price_on_ebay(
    brand: str = None,
    model: str = None,
    barcode: str = None,
    title: str = None
) -> Optional[float]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ebay_service().search_price(brand=brand, model=model, barcode=barcode, title=title)
