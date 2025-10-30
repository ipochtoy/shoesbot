"""Buffer to collect photos for batch processing."""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from time import time
from telegram import File

BUFFER_TIMEOUT = 3.0  # seconds to wait for more photos


class PhotoBuffer:
    def __init__(self):
        self.buffers: Dict[int, List[Tuple[float, File]]] = {}

    def add(self, chat_id: int, photo_file: File) -> Tuple[bool, Optional[List[File]]]:
        """Add photo to buffer. Returns (should_wait, Optional[batch]).
        should_wait=True means this is first photo and we should start timer."""
        now = time()
        
        if chat_id not in self.buffers:
            self.buffers[chat_id] = []
        
        self.buffers[chat_id].append((now, photo_file))
        
        # Clean old buffers
        self._cleanup(now)
        
        # Always return the buffer after adding
        files = [p for _, p in self.buffers[chat_id]]
        is_first = len(files) == 1
        return (is_first, files)

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

