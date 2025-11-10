"""
AI сервис для работы с OpenAI API.

Предоставляет функции для:
- Генерации описаний товаров
- Анализа фото через Vision API
- Автозаполнения карточек товаров
- Работы с голосовыми инструкциями
"""
import os
import json
import re
import logging
from typing import Optional, Dict, List, Any

from .api_client import BaseAPIClient


logger = logging.getLogger(__name__)


class OpenAIService:
    """Сервис для работы с OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API ключ (если None, берется из OPENAI_API_KEY env)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not set")

        self.client = BaseAPIClient(
            base_url='https://api.openai.com/v1',
            timeout=30,
            api_key=self.api_key
        )

    def _call_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = 'gpt-4o',
        max_tokens: int = 200,
        temperature: float = 0.7,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Универсальный метод для вызова Chat Completions API.

        Args:
            messages: Список сообщений для модели
            model: Модель OpenAI
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура для генерации
            timeout: Timeout для запроса

        Returns:
            Текст ответа или None при ошибке
        """
        if not self.api_key:
            return None

        try:
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }

            response = self.client.post(
                'chat/completions',
                json=payload,
                timeout=timeout
            )

            if response.ok:
                data = response.json()
                return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Извлекает JSON из текста (убирает markdown code blocks).

        Args:
            text: Текст с JSON

        Returns:
            Распарсенный JSON или None
        """
        try:
            # Убираем markdown code blocks если есть
            if text.startswith('```'):
                parts = text.split('```')
                if len(parts) > 1:
                    text = parts[1]
                    if text.startswith('json'):
                        text = text[4:]
                text = text.strip()
            elif text.startswith('{'):
                # Начинается с JSON, берем до конца
                end_idx = text.rfind('}')
                if end_idx > 0:
                    text = text[:end_idx + 1]

            return json.loads(text)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None

    def generate_product_description(
        self,
        barcode: str,
        context: str = ""
    ) -> Optional[str]:
        """
        Генерирует описание товара по баркоду и контексту.

        Args:
            barcode: Баркод товара
            context: Дополнительный контекст (текст с фото и т.д.)

        Returns:
            Описание товара или None
        """
        prompt = f'''Ты эксперт по товарам. Найди информацию о товаре с баркодом {barcode}.

{context if context else ""}

Создай краткое описание товара (2-3 предложения) на русском языке для интернет-магазина.
Включи: название товара, бренд (если виден), основные характеристики, материал (если виден).
Будь конкретным и информативным.'''

        messages = [{'role': 'user', 'content': prompt}]
        return self._call_chat_completion(messages, max_tokens=200, temperature=0.7)

    def suggest_category(
        self,
        barcode: str,
        description: str = ""
    ) -> Optional[str]:
        """
        Предлагает категорию товара.

        Args:
            barcode: Баркод товара
            description: Описание товара

        Returns:
            Категория товара или None
        """
        prompt = f'''Определи категорию товара по баркоду {barcode} и описанию:

{description}

Ответь одним словом - категорией товара (например: Обувь, Одежда, Аксессуары, Косметика).
Только категория, без дополнительного текста.'''

        messages = [{'role': 'user', 'content': prompt}]
        return self._call_chat_completion(messages, max_tokens=50, temperature=0.3, timeout=15)

    def suggest_price(
        self,
        barcode: str,
        description: str = "",
        brand: str = ""
    ) -> Optional[float]:
        """
        Предлагает примерную цену товара.

        Args:
            barcode: Баркод товара
            description: Описание товара
            brand: Бренд товара

        Returns:
            Цена в долларах или None
        """
        prompt = f'''Оцени примерную стоимость товара:

Баркод: {barcode}
Бренд: {brand}
Описание: {description}

Ответь только числом (цена в долларах США), без текста и символов валюты.
Если не можешь определить - ответь "0".'''

        messages = [{'role': 'user', 'content': prompt}]
        text = self._call_chat_completion(messages, max_tokens=50, temperature=0.3, timeout=15)

        if text:
            # Извлекаем число
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                return float(numbers[0])

        return None

    def analyze_photos_with_vision(
        self,
        photo_urls: List[str],
        max_photos: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Анализирует фото через OpenAI Vision и возвращает описание товара.

        Args:
            photo_urls: Список URL фотографий
            max_photos: Максимальное количество фото для анализа

        Returns:
            Словарь с информацией о товаре или None
        """
        if not self.api_key or not photo_urls:
            return None

        try:
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

            # Добавляем фото (максимум max_photos)
            for photo_url in photo_urls[:max_photos]:
                if photo_url.startswith('http'):
                    content.append({
                        'type': 'image_url',
                        'image_url': {'url': photo_url}
                    })

            messages = [{'role': 'user', 'content': content}]
            text = self._call_chat_completion(
                messages,
                max_tokens=1000,
                temperature=0.3,
                timeout=30
            )

            if text:
                result = self._extract_json_from_text(text)
                if result:
                    return result
                # Если не JSON, возвращаем как description
                return {'description': text}

            return None

        except Exception as e:
            logger.error(f"Vision API error: {e}", exc_info=True)
            return None

    def auto_fill_product_card(
        self,
        card_data: Dict[str, Any],
        photo_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Автоматически заполняет карточку товара используя AI с анализом фото.

        Args:
            card_data: Данные карточки (barcodes, photos_text, brand)
            photo_urls: URL фотографий для анализа

        Returns:
            Словарь с заполненными полями (description, category, price, etc.)
        """
        results = {}

        # Собираем информацию
        barcodes = [b.get('data', '') for b in card_data.get('barcodes', [])]
        main_barcode = barcodes[0] if barcodes else ''

        # Анализируем фото через Vision API (приоритет)
        if photo_urls:
            vision_result = self.analyze_photos_with_vision(photo_urls)
            if vision_result:
                results.update(vision_result)

        # Если Vision не дал результатов, используем текстовый метод
        if not results and main_barcode:
            description = self.generate_product_description(
                main_barcode,
                card_data.get('photos_text', '')
            )
            if description:
                results['description'] = description

            category = self.suggest_category(main_barcode, results.get('description', ''))
            if category:
                results['category'] = category

            price = self.suggest_price(
                main_barcode,
                results.get('description', ''),
                card_data.get('brand', '')
            )
            if price and price > 0:
                results['price'] = price

        return results

    def generate_from_instruction(
        self,
        instruction: str,
        photo_urls: Optional[List[str]] = None,
        max_photos: int = 3
    ) -> Dict[str, Any]:
        """
        Генерирует описание товара по голосовой инструкции.

        Args:
            instruction: Текстовая инструкция пользователя
            photo_urls: URL фотографий (опционально)
            max_photos: Максимальное количество фото для анализа

        Returns:
            Словарь с информацией о товаре
        """
        if not self.api_key:
            return {}

        try:
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
                for photo_url in photo_urls[:max_photos]:
                    if photo_url.startswith('http'):
                        content.append({
                            'type': 'image_url',
                            'image_url': {'url': photo_url}
                        })

            logger.info(f"Sending instruction request with {len(photo_urls) if photo_urls else 0} photos")

            messages = [{'role': 'user', 'content': content}]
            text = self._call_chat_completion(
                messages,
                max_tokens=1000,
                temperature=0.7,
                timeout=30
            )

            if text:
                logger.info(f"Response text (first 500 chars): {text[:500]}")
                result = self._extract_json_from_text(text)

                if result:
                    # Проверяем обязательные поля
                    if not result.get('title') or not result.get('description'):
                        result['title'] = result.get('title') or instruction[:50] or 'Товар'
                        result['description'] = result.get('description') or f'Описание товара: {instruction}'
                    return result

                # Если не получилось распарсить JSON
                if 'description' in text.lower() or len(text) > 50:
                    return {'description': text}

            return {}

        except Exception as e:
            logger.error(f"Instruction generation error: {e}", exc_info=True)
            return {}

    def search_product_info(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Поиск информации о товаре по баркоду через OpenAI.

        Args:
            barcode: Баркод товара

        Returns:
            Словарь с информацией о товаре или None
        """
        if not self.api_key:
            return None

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

        messages = [{'role': 'user', 'content': prompt}]
        text = self._call_chat_completion(
            messages,
            max_tokens=300,
            temperature=0.3,
            timeout=20
        )

        if text:
            result = self._extract_json_from_text(text)
            if result:
                # Убираем null значения
                return {k: v for k, v in result.items() if v is not None and v != 'null'}

        return None

    def generate_product_summary(
        self,
        photo_data_list: Optional[List[Dict[str, str]]] = None,
        photo_urls: Optional[List[str]] = None,
        barcodes: Optional[List[str]] = None,
        gg_labels: Optional[List[str]] = None,
        ebay_price: Optional[float] = None,
        max_photos: int = 2
    ) -> Optional[str]:
        """
        Генерирует полную сводку о товаре на основе фото и баркодов.

        Args:
            photo_data_list: Список словарей с ключами 'base64' и 'mime_type'
            photo_urls: Список URL изображений (альтернатива photo_data_list)
            barcodes: Список баркодов
            gg_labels: Список GG лейблов
            ebay_price: Цена с eBay (если найдена)
            max_photos: Максимальное количество фото для анализа

        Returns:
            Текстовая сводка или None
        """
        if not self.api_key:
            return None

        if not photo_data_list and not photo_urls:
            logger.warning("No photo data or URLs provided")
            return None

        try:
            # Формируем контекст с баркодами
            context_parts = []
            if barcodes:
                context_parts.append(f"Найденные баркоды: {', '.join(barcodes[:5])}")
            if gg_labels:
                context_parts.append(f"Наши лейбы GG: {', '.join(gg_labels)}")
            if ebay_price:
                context_parts.append(
                    f"Найдена цена на eBay: ${ebay_price:.2f}"
                )

            context_text = "\n".join(context_parts) if context_parts else ""

            # Формируем текст для секции цены
            if ebay_price:
                price_instruction = f"Используй найденную цену на eBay: {ebay_price:.0f} USD"
            else:
                price_instruction = (
                    "ОБЯЗАТЕЛЬНО оцени примерную розничную цену этого товара в USD, "
                    "используя свои знания о ценах на подобные товары и бренды."
                )

            # Формируем контент с фото
            content = [{
                'type': 'text',
                'text': f'''OCR Task: Read text from retail product labels/tags.

{context_text if context_text else ""}

Extract visible text and fill template below in Russian:

**Что это за товар:**
ОБЯЗАТЕЛЬНО включи бренд в описание. Формат: "Тип товара от [БРЕНД]".

**Бренд и модель:**
Полное название бренда с этикетки.

**Размер и характеристики:**
Размер (S/M/L/XL или числа), материал, состав ткани.

**Цвет:**
Один цвет словом по-русски.

**Состояние товара:**
new

**Особенности:**
Технические характеристики если есть на этикетке.

**Температурный режим / Назначение:**
Если указан диапазон температур.

**Производитель:**
Страна если видно.

**Рекомендуемая розничная цена (USD):**
{price_instruction}

**Описание для продажи:**
3-4 предложения про материал, характеристики, применение на основе информации с этикетки.

Just read and transcribe label text.'''
            }]

            # Добавляем фото (приоритет: base64 данные, затем URL)
            if photo_data_list:
                for photo_data in photo_data_list[:max_photos]:
                    if isinstance(photo_data, dict) and 'base64' in photo_data:
                        content.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:{photo_data.get('mime_type', 'image/jpeg')};base64,{photo_data['base64']}"
                            }
                        })
            elif photo_urls:
                for photo_url in photo_urls[:max_photos]:
                    if photo_url.startswith('http'):
                        content.append({
                            'type': 'image_url',
                            'image_url': {'url': photo_url}
                        })

            logger.info(f"Generating summary with {len([c for c in content if c.get('type') == 'image_url'])} images")

            messages = [{'role': 'user', 'content': content}]
            text = self._call_chat_completion(
                messages,
                model='gpt-4o-mini',  # Используем mini - мягче политики контента
                max_tokens=1200,
                temperature=0.3,
                timeout=30
            )

            if text:
                logger.info(f"Summary received: {len(text)} characters")
            else:
                logger.warning("Summary text is empty")

            return text

        except Exception as e:
            logger.error(f"Summary generation error: {e}", exc_info=True)
            return None

    def close(self):
        """Закрывает клиент."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance для обратной совместимости
_default_service = None


def get_ai_service() -> OpenAIService:
    """Возвращает singleton instance OpenAIService."""
    global _default_service
    if _default_service is None:
        _default_service = OpenAIService()
    return _default_service


# Функции-обертки для обратной совместимости со старым API
def generate_product_description(barcode: str, photos_text: str = "") -> Optional[str]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().generate_product_description(barcode, photos_text)


def suggest_category(barcode: str, description: str = "") -> Optional[str]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().suggest_category(barcode, description)


def suggest_price(barcode: str, description: str = "", brand: str = "") -> Optional[float]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().suggest_price(barcode, description, brand)


def analyze_photos_with_vision(photo_urls: List[str]) -> Optional[Dict]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().analyze_photos_with_vision(photo_urls)


def auto_fill_product_card(card_data: Dict, photo_urls: List[str] = None) -> Dict:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().auto_fill_product_card(card_data, photo_urls)


def generate_from_instruction(instruction: str, photo_urls: List[str] = None, card=None) -> Dict:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().generate_from_instruction(instruction, photo_urls)


def search_product_with_openai(barcode: str) -> Optional[Dict]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().search_product_info(barcode)


def generate_product_summary(
    photo_data_list: List[Dict] = None,
    photo_urls: List[str] = None,
    barcodes: List[str] = None,
    gg_labels: List[str] = None
) -> Optional[str]:
    """Обратная совместимость с ai_helpers.py"""
    return get_ai_service().generate_product_summary(
        photo_data_list=photo_data_list,
        photo_urls=photo_urls,
        barcodes=barcodes,
        gg_labels=gg_labels
    )
