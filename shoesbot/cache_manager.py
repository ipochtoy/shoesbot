"""Simple file-based cache for Vision API results."""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Optional
from shoesbot.models import Barcode
from shoesbot.logging_setup import logger


class VisionCache:
    """File-based cache for Vision API results using SHA256 hashes."""

    def __init__(self, cache_dir: str = ".vision_cache"):
        """Initialize cache with specified directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.hits = 0
        self.misses = 0
        logger.info(f"VisionCache initialized: {self.cache_dir.absolute()}")

    def _get_hash(self, image_bytes: bytes) -> str:
        """Generate SHA256 hash of image bytes."""
        return hashlib.sha256(image_bytes).hexdigest()

    def _get_cache_path(self, image_hash: str) -> Path:
        """Get cache file path for given hash."""
        # Use subdirectories to avoid too many files in one directory
        subdir = image_hash[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / f"{image_hash}.json"

    def get(self, image_bytes: bytes) -> Optional[List[Barcode]]:
        """Get cached results for image. Returns None if not cached."""
        image_hash = self._get_hash(image_bytes)
        cache_path = self._get_cache_path(image_hash)

        if not cache_path.exists():
            self.misses += 1
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct Barcode objects
            barcodes = [
                Barcode(
                    symbology=item['symbology'],
                    data=item['data'],
                    source=item['source']
                )
                for item in data
            ]

            self.hits += 1
            logger.debug(f"VisionCache HIT: {image_hash[:8]}... ({len(barcodes)} barcodes)")
            return barcodes

        except Exception as e:
            logger.warning(f"VisionCache read error for {image_hash[:8]}: {e}")
            self.misses += 1
            return None

    def put(self, image_bytes: bytes, barcodes: List[Barcode]) -> None:
        """Store results in cache."""
        image_hash = self._get_hash(image_bytes)
        cache_path = self._get_cache_path(image_hash)

        try:
            # Convert Barcode objects to dict
            data = [
                {
                    'symbology': bc.symbology,
                    'data': bc.data,
                    'source': bc.source
                }
                for bc in barcodes
            ]

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"VisionCache PUT: {image_hash[:8]}... ({len(barcodes)} barcodes)")

        except Exception as e:
            logger.warning(f"VisionCache write error for {image_hash[:8]}: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        # Count total cached files
        cached_files = sum(1 for _ in self.cache_dir.rglob("*.json"))

        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 2),
            'cached_files': cached_files,
        }

    def clear(self) -> int:
        """Clear all cached files. Returns number of files deleted."""
        count = 0
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {cache_file}: {e}")

        logger.info(f"VisionCache cleared: {count} files deleted")
        return count


# Global cache instance
_cache_instance: Optional[VisionCache] = None


def get_cache() -> VisionCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.getenv("VISION_CACHE_DIR", ".vision_cache")
        _cache_instance = VisionCache(cache_dir)
    return _cache_instance
