"""Helper functions for the Telegram bot."""
import asyncio
from io import BytesIO
from typing import Callable, Any, TypeVar, Dict
from datetime import datetime, timedelta

from shoesbot.config import config
from shoesbot.logging_setup import logger


T = TypeVar('T')


async def retry_async(
    func: Callable[..., Any],
    *args,
    max_retries: int = None,
    **kwargs
) -> T:
    """
    Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retries (default: config.MAX_RETRIES)
        **kwargs: Keyword arguments for func

    Returns:
        Result of func if successful

    Raises:
        Last exception if all retries failed
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES

    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = config.get_retry_delay(attempt)
                logger.warning(
                    f"retry_async: {func.__name__} attempt {attempt+1}/{max_retries} "
                    f"failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"retry_async: {func.__name__} failed after {max_retries} attempts: {e}")

    raise last_error


async def download_telegram_photo(file_obj, max_size_mb: int = 10) -> BytesIO:
    """
    Download telegram photo with size validation.

    Args:
        file_obj: Telegram File object
        max_size_mb: Maximum allowed file size in MB

    Returns:
        BytesIO buffer with photo data

    Raises:
        ValueError: If photo exceeds max_size_mb
    """
    buf = BytesIO()
    await file_obj.download_to_memory(out=buf)

    size_bytes = len(buf.getvalue())
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > max_size_mb:
        raise ValueError(f"Photo size {size_mb:.2f}MB exceeds maximum {max_size_mb}MB")

    buf.seek(0)
    return buf


def cleanup_old_entries(data_dict: Dict[Any, Any], ttl_hours: int) -> int:
    """
    Clean up old entries from dict (for memory management).

    Removes entries that have 'timestamp' field older than ttl_hours.
    If entry doesn't have 'timestamp', it's not removed.

    Args:
        data_dict: Dictionary to clean up
        ttl_hours: Time-to-live in hours

    Returns:
        Number of entries removed
    """
    if not data_dict:
        return 0

    cutoff_time = datetime.now() - timedelta(hours=ttl_hours)
    keys_to_remove = []

    for key, value in data_dict.items():
        # Check if value has timestamp and if it's old
        if isinstance(value, dict) and 'timestamp' in value:
            timestamp = value['timestamp']
            if isinstance(timestamp, datetime) and timestamp < cutoff_time:
                keys_to_remove.append(key)

    for key in keys_to_remove:
        data_dict.pop(key, None)

    if keys_to_remove:
        logger.info(f"cleanup_old_entries: removed {len(keys_to_remove)} old entries")

    return len(keys_to_remove)
