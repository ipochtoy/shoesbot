"""
Базовый API клиент для HTTP запросов с retry, timeout и логированием.

Устраняет дублирование кода для всех внешних API запросов.
"""
import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator для retry логики с exponential backoff.

    Args:
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками в секундах
        backoff: Множитель для exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed: {e}")

            raise last_exception

        return wrapper
    return decorator


class BaseAPIClient:
    """
    Базовый класс для всех API клиентов.

    Предоставляет:
    - Retry логику (3 попытки, exponential backoff)
    - Timeout настройку
    - Логирование всех запросов
    - Обработка ошибок
    - Session с connection pooling
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        api_key: Optional[str] = None
    ):
        """
        Args:
            base_url: Базовый URL для API
            timeout: Timeout для запросов в секундах
            max_retries: Максимальное количество повторных попыток
            api_key: API ключ для авторизации
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key

        # Создаем session с retry логикой
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Создает requests.Session с настроенным retry."""
        session = requests.Session()

        # Настройка retry для определенных HTTP статусов
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # 1s, 2s, 4s, ...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Формирует заголовки для запроса.

        Args:
            custom_headers: Дополнительные заголовки

        Returns:
            Словарь с заголовками
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ShoesBot/1.0'
        }

        # Добавляем API ключ если есть
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        # Объединяем с custom headers (они имеют приоритет)
        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _log_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ):
        """Логирует запрос."""
        logger.info(f"{method} {url}")
        if params:
            logger.debug(f"Params: {params}")
        if data:
            # Логируем только первые 500 символов данных
            data_str = str(data)
            if len(data_str) > 500:
                data_str = data_str[:500] + "..."
            logger.debug(f"Data: {data_str}")

    def _log_response(self, response: requests.Response):
        """Логирует ответ."""
        logger.info(f"Response: {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"Error response: {response.text[:500]}")

    def _build_url(self, endpoint: str) -> str:
        """
        Строит полный URL из base_url и endpoint.

        Args:
            endpoint: Endpoint (может быть полным URL или относительным путем)

        Returns:
            Полный URL
        """
        # Если endpoint уже полный URL, используем его
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            return endpoint

        # Иначе добавляем к base_url
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}" if self.base_url else endpoint

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> requests.Response:
        """
        Выполняет GET запрос.

        Args:
            endpoint: Endpoint или полный URL
            params: Query параметры
            headers: Дополнительные заголовки
            timeout: Timeout для запроса (переопределяет self.timeout)

        Returns:
            Response объект

        Raises:
            requests.RequestException: При ошибке запроса
        """
        url = self._build_url(endpoint)
        headers = self._get_headers(headers)
        timeout = timeout or self.timeout

        self._log_request('GET', url, params=params)

        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )

        self._log_response(response)
        return response

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> requests.Response:
        """
        Выполняет POST запрос.

        Args:
            endpoint: Endpoint или полный URL
            data: Form data
            json: JSON данные
            headers: Дополнительные заголовки
            timeout: Timeout для запроса (переопределяет self.timeout)

        Returns:
            Response объект

        Raises:
            requests.RequestException: При ошибке запроса
        """
        url = self._build_url(endpoint)
        headers = self._get_headers(headers)
        timeout = timeout or self.timeout

        self._log_request('POST', url, data=json or data)

        response = self.session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout
        )

        self._log_response(response)
        return response

    def get_json(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Выполняет GET запрос и возвращает JSON.

        Args:
            endpoint: Endpoint или полный URL
            params: Query параметры
            **kwargs: Дополнительные аргументы для get()

        Returns:
            Распарсенный JSON ответ

        Raises:
            requests.RequestException: При ошибке запроса
            ValueError: При ошибке парсинга JSON
        """
        response = self.get(endpoint, params=params, **kwargs)
        response.raise_for_status()
        return response.json()

    def post_json(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Выполняет POST запрос и возвращает JSON.

        Args:
            endpoint: Endpoint или полный URL
            data: JSON данные для отправки
            **kwargs: Дополнительные аргументы для post()

        Returns:
            Распарсенный JSON ответ

        Raises:
            requests.RequestException: При ошибке запроса
            ValueError: При ошибке парсинга JSON
        """
        response = self.post(endpoint, json=data, **kwargs)
        response.raise_for_status()
        return response.json()

    def close(self):
        """Закрывает session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
