"""
FASHN AI API сервис для генерации фото моделей в одежде.

Предоставляет функции для:
- Product to Model генерации
- Смены фона
- Polling статуса задач
"""
import os
import time
import logging
from typing import Optional

from .api_client import BaseAPIClient


logger = logging.getLogger(__name__)


class FashnService:
    """Сервис для работы с FASHN AI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: FASHN API ключ (если None, берется из FASHN_API_KEY env)
        """
        self.api_key = api_key or os.getenv('FASHN_API_KEY')
        if not self.api_key:
            logger.warning("FASHN API key not set")

        self.client = BaseAPIClient(
            base_url='https://api.fashn.ai/v1',
            timeout=30,
            api_key=self.api_key
        )

    def _poll_prediction_status(
        self,
        prediction_id: str,
        max_attempts: int = 60,
        poll_interval: int = 2
    ) -> Optional[str]:
        """
        Универсальная функция для polling статуса задачи.

        Args:
            prediction_id: ID предсказания
            max_attempts: Максимальное количество попыток
            poll_interval: Интервал между попытками в секундах

        Returns:
            URL сгенерированного изображения или None при ошибке
        """
        logger.info(f"Polling status for prediction {prediction_id}")

        for attempt in range(1, max_attempts + 1):
            time.sleep(poll_interval)

            try:
                response = self.client.get(f'status/{prediction_id}')

                if not response.ok:
                    logger.error(f"Status check failed: {response.status_code}")
                    continue

                status_data = response.json()
                status = status_data.get('status')

                logger.debug(f"Attempt {attempt}/{max_attempts}: status={status}")

                if status == 'completed':
                    output = status_data.get('output')
                    if output and len(output) > 0:
                        image_url = output[0]
                        logger.info(f"Generation completed: {image_url}")
                        return image_url
                    else:
                        logger.error("No output in completed response")
                        return None

                elif status == 'failed':
                    error = status_data.get('error', {})
                    logger.error(f"Generation failed: {error}")
                    return None

                # Status: pending or processing - continue polling

            except Exception as e:
                logger.warning(f"Error during polling: {e}")
                continue

        logger.error(f"Timeout after {max_attempts} attempts")
        return None

    def generate_model_with_product(
        self,
        product_image_url: str,
        prompt: Optional[str] = None,
        resolution: str = '1k',
        aspect_ratio: Optional[str] = None,
        max_wait_seconds: int = 120
    ) -> Optional[str]:
        """
        Генерирует фото модели в одежде через FASHN AI Product to Model.

        Args:
            product_image_url: Публичный URL фото товара
            prompt: Текстовые инструкции ("professional studio photo", "man with tattoos")
            resolution: "1k" (точный) или "4k" (креативный HD)
            aspect_ratio: "1:1", "3:4", "9:16" и т.д. (опционально)
            max_wait_seconds: Максимальное время ожидания в секундах

        Returns:
            URL сгенерированного изображения или None при ошибке
        """
        if not self.api_key:
            logger.error("FASHN API key not set")
            return None

        logger.info("=" * 70)
        logger.info("FASHN AI - Product to Model")
        logger.info("=" * 70)
        logger.info(f"Product URL: {product_image_url}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Resolution: {resolution}")

        try:
            # 1. Submit задачу
            logger.info("Step 1: Submitting to FASHN API...")

            inputs = {
                'product_image': product_image_url,
                'output_format': 'jpeg',
                'resolution': resolution,
            }

            if prompt:
                inputs['prompt'] = prompt
            if aspect_ratio:
                inputs['aspect_ratio'] = aspect_ratio

            payload = {
                'model_name': 'product-to-model',
                'inputs': inputs
            }

            response = self.client.post('run', json=payload)

            if not response.ok:
                logger.error(f"Submit failed: {response.status_code}")
                return None

            result = response.json()

            if 'error' in result and result['error']:
                logger.error(f"Submit error: {result['error']}")
                return None

            prediction_id = result.get('id')
            if not prediction_id:
                logger.error("No prediction ID in response")
                return None

            logger.info(f"Prediction ID: {prediction_id}")

            # 2. Poll статус
            logger.info("Step 2: Polling status...")
            max_attempts = max_wait_seconds // 2  # Polling каждые 2 секунды
            return self._poll_prediction_status(prediction_id, max_attempts=max_attempts)

        except Exception as e:
            logger.error(f"Exception in generate_model_with_product: {e}", exc_info=True)
            return None

    def change_background(
        self,
        image_url: str,
        background_prompt: str = "studio background",
        max_wait_seconds: int = 80
    ) -> Optional[str]:
        """
        Меняет фон через FASHN Background Change.

        Args:
            image_url: Публичный URL изображения
            background_prompt: Описание фона
            max_wait_seconds: Максимальное время ожидания в секундах

        Returns:
            URL обработанного изображения или None при ошибке
        """
        if not self.api_key:
            logger.error("FASHN API key not set")
            return None

        logger.info("=" * 70)
        logger.info("FASHN Background Change")
        logger.info(f"Image: {image_url}")
        logger.info(f"Prompt: {background_prompt}")

        try:
            payload = {
                'model_name': 'background-change',
                'inputs': {
                    'image': image_url,
                    'prompt': background_prompt,
                    'output_format': 'jpeg'
                }
            }

            response = self.client.post('run', json=payload)

            if not response.ok:
                logger.error(f"Submit failed: {response.status_code}")
                return None

            prediction_id = response.json().get('id')
            if not prediction_id:
                logger.error("No prediction ID in response")
                return None

            logger.info(f"Prediction ID: {prediction_id}")

            # Poll статус
            max_attempts = max_wait_seconds // 2
            return self._poll_prediction_status(prediction_id, max_attempts=max_attempts)

        except Exception as e:
            logger.error(f"Exception in change_background: {e}", exc_info=True)
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


# Singleton instance
_default_service = None


def get_fashn_service() -> FashnService:
    """Возвращает singleton instance FashnService."""
    global _default_service
    if _default_service is None:
        _default_service = FashnService()
    return _default_service


# Функции-обертки для обратной совместимости со старым API
def generate_model_with_product(
    product_image_url: str,
    prompt: Optional[str] = None,
    resolution: str = '1k',
    aspect_ratio: Optional[str] = None
) -> Optional[str]:
    """Обратная совместимость с fashn_api.py"""
    return get_fashn_service().generate_model_with_product(
        product_image_url=product_image_url,
        prompt=prompt,
        resolution=resolution,
        aspect_ratio=aspect_ratio
    )


def change_background(image_url: str, background_prompt: str = "studio background") -> Optional[str]:
    """Обратная совместимость с fashn_api.py"""
    return get_fashn_service().change_background(image_url, background_prompt)
