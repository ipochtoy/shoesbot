"""Buffer to collect photos for batch processing."""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, NamedTuple
from time import time
from telegram import File
import logging

BUFFER_TIMEOUT = 3.0  # seconds to wait for more photos

logger = logging.getLogger("shoesbot.photo_buffer")


class PhotoItem(NamedTuple):
    """Photo with file_id for media group and File for processing."""
    file_id: str
    file_obj: File


class PhotoBuffer:
    def __init__(self):
        self.buffers: Dict[int, List[Tuple[float, PhotoItem]]] = {}

    def add(self, chat_id: int, file_id: str, photo_file: File) -> Tuple[bool, Optional[List[PhotoItem]]]:
        """Add photo to buffer. Returns (should_wait, Optional[batch]).
        should_wait=True means this is first photo and we should start timer."""
        now = time()
        
        if chat_id not in self.buffers:
            self.buffers[chat_id] = []
        
        self.buffers[chat_id].append((now, PhotoItem(file_id, photo_file)))
        
        # Clean old buffers
        self._cleanup(now)
        
        # Always return the buffer after adding
        items = [p for _, p in self.buffers[chat_id]]
        is_first = len(items) == 1
        return (is_first, items)

    def flush(self, chat_id: int, timeout: float = BUFFER_TIMEOUT) -> Optional[List[PhotoItem]]:
        """Flush buffer for chat_id after timeout."""
        logger.info(f"flush: called for chat_id={chat_id}, timeout={timeout}")
        if chat_id not in self.buffers:
            logger.warning(f"flush: chat_id {chat_id} not in buffers")
            return None
        
        now = time()
        logger.info(f"flush: before cleanup, buffer[{chat_id}] size: {len(self.buffers[chat_id])}")
        self._cleanup(now)
        logger.info(f"flush: after cleanup, buffer[{chat_id}] exists: {chat_id in self.buffers}")
        
        if not self.buffers.get(chat_id):
            logger.warning(f"flush: buffer[{chat_id}] empty after cleanup")
            return None
        
        # Get FIRST photo time (when we started waiting)
        first_time = min(t for t, _ in self.buffers[chat_id])
        time_diff = now - first_time
        logger.info(f"flush: first_time={first_time}, now={now}, diff={time_diff:.2f}s, timeout={timeout}")
        
        # Flush after timeout from FIRST photo
        if now - first_time >= timeout:
            items = [p for _, p in self.buffers[chat_id]]
            logger.info(f"flush: returning {len(items)} items")
            del self.buffers[chat_id]
            return items
        
        logger.warning(f"flush: not yet timeout, returning None")
        return None

    def _cleanup(self, now: float):
        """Remove old buffers."""
        for chat_id in list(self.buffers.keys()):
            if not self.buffers[chat_id]:
                del self.buffers[chat_id]
                continue


# Global buffer instance
buffer = PhotoBuffer()

