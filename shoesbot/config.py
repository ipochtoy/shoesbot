"""Configuration constants for the Telegram bot."""
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class BotConfig:
    """Bot configuration with all magic numbers and constants."""

    # Buffer settings
    BUFFER_TIMEOUT: Final[float] = 3.0
    BUFFER_WAIT_TIME: Final[float] = 3.2
    MAX_PHOTOS_IN_BATCH: Final[int] = 10

    # Retry settings
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAY_BASE: Final[float] = 0.5

    # API timeouts
    TELEGRAM_CONNECT_TIMEOUT: Final[float] = 10.0
    TELEGRAM_READ_TIMEOUT: Final[float] = 20.0
    TELEGRAM_WRITE_TIMEOUT: Final[float] = 20.0
    TELEGRAM_POOL_TIMEOUT: Final[float] = 30.0
    TELEGRAM_MEDIA_WRITE_TIMEOUT: Final[float] = 30.0
    OPENAI_TIMEOUT: Final[int] = 15
    DJANGO_TIMEOUT: Final[int] = 10

    # Connection pool
    CONNECTION_POOL_SIZE: Final[int] = 20

    # Memory cleanup
    PENDING_TTL_HOURS: Final[int] = 24
    SENT_BATCHES_TTL_HOURS: Final[int] = 48
    CLEANUP_INTERVAL_SECONDS: Final[int] = 3600  # 1 hour

    # Message delays (for stability)
    MESSAGE_DELAY: Final[float] = 0.2

    # OpenAI
    OPENAI_MODEL: Final[str] = 'gpt-4o-mini'
    OPENAI_MAX_TOKENS: Final[int] = 50
    OPENAI_TEMPERATURE: Final[float] = 0.0

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for retry attempt."""
        return self.RETRY_DELAY_BASE * (2 ** attempt)

    def get_adaptive_buffer_timeout(self, current_count: int) -> float:
        """
        Calculate adaptive buffer timeout based on current photo count.

        Strategy:
        - 1 photo: 2.0s (quick single photo)
        - 2-3 photos: 3.0s (normal batch)
        - 4-5 photos: 4.0s (medium batch)
        - 6+ photos: 5.0s (large batch, wait for more)
        """
        if current_count == 1:
            return 2.0
        elif current_count <= 3:
            return 3.0
        elif current_count <= 5:
            return 4.0
        else:
            return 5.0


# Global config instance
config = BotConfig()
