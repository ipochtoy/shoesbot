"""Message sender with retry logic for Telegram bot."""
import asyncio
from typing import Optional, List

from telegram import Bot, Message
from telegram.error import TelegramError

from shoesbot.config import config
from shoesbot.logging_setup import logger


class MessageSender:
    """Handles sending messages and media with automatic retry logic."""

    def __init__(self, bot: Bot):
        """
        Initialize MessageSender.

        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        reply_markup=None,
        max_retries: Optional[int] = None
    ) -> bool:
        """
        Send message with retry logic.

        Args:
            chat_id: Chat ID to send to
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_markup: Reply markup
            max_retries: Maximum retries (default: config.MAX_RETRIES)

        Returns:
            True if successful, False otherwise
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    chat_id,
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                return True
            except TelegramError as e:
                if attempt < max_retries - 1:
                    wait_time = config.get_retry_delay(attempt)
                    logger.warning(
                        f"MessageSender.send_message: attempt {attempt+1}/{max_retries} "
                        f"failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MessageSender.send_message: failed after {max_retries} attempts: {e}")
                    return False
        return False

    async def send_message_ret(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        reply_markup=None,
        max_retries: Optional[int] = None
    ) -> Optional[Message]:
        """
        Send message with retry logic and return Message object.

        Args:
            chat_id: Chat ID to send to
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_markup: Reply markup
            max_retries: Maximum retries (default: config.MAX_RETRIES)

        Returns:
            Message object if successful, None otherwise
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                return await self.bot.send_message(
                    chat_id,
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            except TelegramError as e:
                if attempt < max_retries - 1:
                    wait_time = config.get_retry_delay(attempt)
                    logger.warning(
                        f"MessageSender.send_message_ret: retry {attempt+1}/{max_retries} "
                        f"in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MessageSender.send_message_ret: failed after retries: {e}")
                    return None
        return None

    async def send_media_group(
        self,
        chat_id: int,
        media_group: list,
        max_retries: Optional[int] = None
    ) -> bool:
        """
        Send media group with retry logic.

        Args:
            chat_id: Chat ID to send to
            media_group: List of InputMedia objects
            max_retries: Maximum retries (default: config.MAX_RETRIES)

        Returns:
            True if successful, False otherwise
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                await self.bot.send_media_group(chat_id, media_group)
                return True
            except TelegramError as e:
                if attempt < max_retries - 1:
                    wait_time = config.get_retry_delay(attempt)
                    logger.warning(
                        f"MessageSender.send_media_group: attempt {attempt+1}/{max_retries} "
                        f"failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MessageSender.send_media_group: failed after {max_retries} attempts: {e}")
                    return False
        return False

    async def send_media_group_ret(
        self,
        chat_id: int,
        media_group: list,
        max_retries: Optional[int] = None
    ) -> List[Message]:
        """
        Send media group with retry logic and return Message objects.

        Args:
            chat_id: Chat ID to send to
            media_group: List of InputMedia objects
            max_retries: Maximum retries (default: config.MAX_RETRIES)

        Returns:
            List of Message objects if successful, empty list otherwise
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                return await self.bot.send_media_group(chat_id, media_group)
            except TelegramError as e:
                if attempt < max_retries - 1:
                    wait_time = config.get_retry_delay(attempt)
                    logger.warning(
                        f"MessageSender.send_media_group_ret: retry {attempt+1}/{max_retries} "
                        f"in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MessageSender.send_media_group_ret: failed after retries: {e}")
                    return []
        return []
