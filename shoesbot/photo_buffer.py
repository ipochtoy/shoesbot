"""Buffer to collect photos for batch processing."""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from time import time
from telegram import File

BUFFER_TIMEOUT = 3.0  # seconds to wait for more photos


class PhotoBuffer:
    def __init__(self):
        self.buffers: Dict[int, List[Tuple[float, File]]] = {}

    def add(self, chat_id: int, photo_file: File) -> Optional[List[File]]:
        """Add photo to buffer. Returns list of photos if buffer is ready, None otherwise."""
        now = time()
        
        if chat_id not in self.buffers:
            self.buffers[chat_id] = []
        
        self.buffers[chat_id].append((now, photo_file))
        
        # Clean old buffers
        self._cleanup(now)
        
        # If this is the first photo, return None (wait for more)
        if len(self.buffers[chat_id]) == 1:
            return None
        
        # Return all photos in buffer
        files = [p for _, p in self.buffers[chat_id]]
        return files

    def flush(self, chat_id: int, timeout: float = BUFFER_TIMEOUT) -> Optional[List[File]]:
        """Check if buffer should be flushed due to timeout."""
        if chat_id not in self.buffers:
            return None
        
        now = time()
        self._cleanup(now)
        
        if not self.buffers[chat_id]:
            return None
        
        # Get latest photo time
        latest_time = max(t for t, _ in self.buffers[chat_id])
        
        if now - latest_time > timeout:
            files = [p for _, p in self.buffers[chat_id]]
            del self.buffers[chat_id]
            return files
        
        return None

    def _cleanup(self, now: float):
        """Remove old buffers."""
        for chat_id in list(self.buffers.keys()):
            if not self.buffers[chat_id]:
                del self.buffers[chat_id]
                continue


# Global buffer instance
buffer = PhotoBuffer()

