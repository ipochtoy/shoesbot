from typing import List
import os
import re
import base64
import time
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder
from shoesbot.cache_manager import get_cache
from shoesbot.logging_setup import logger

class VisionDecoder(Decoder):
    name = "vision-ocr"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        # Check cache first
        cache = get_cache()
        cached_result = cache.get(image_bytes)
        if cached_result is not None:
            return cached_result

        # Try REST API with API key first (with retry logic)
        api_key = os.getenv("GOOGLE_VISION_API_KEY")
        if api_key:
            result = self._try_rest_api_with_retry(image_bytes, api_key, cache)
            if result is not None:
                return result

        # Fallback to credentials JSON file (with retry logic)
        result = self._try_credentials_api_with_retry(image_bytes, cache)
        if result is not None:
            return result

        return []

    def _try_rest_api_with_retry(self, image_bytes: bytes, api_key: str, cache, max_retries: int = 3) -> List[Barcode]:
        """Try REST API with exponential backoff retry."""
        import requests

        for attempt in range(max_retries):
            try:
                img_b64 = base64.b64encode(image_bytes).decode()
                url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
                payload = {
                    "requests": [{
                        "image": {"content": img_b64},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }]
                }
                resp = requests.post(url, json=payload, timeout=5)

                if resp.ok:
                    data = resp.json()
                    if "responses" in data and data["responses"]:
                        text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                        barcodes = self._extract_barcodes(text)
                        # Cache the result
                        cache.put(image_bytes, barcodes)
                        logger.debug(f"VisionDecoder REST API success (attempt {attempt+1})")
                        return barcodes
                else:
                    logger.warning(f"VisionDecoder REST API failed: {resp.status_code} (attempt {attempt+1}/{max_retries})")

            except requests.Timeout as e:
                logger.warning(f"VisionDecoder REST API timeout (attempt {attempt+1}/{max_retries}): {e}")
            except Exception as e:
                logger.warning(f"VisionDecoder REST API error (attempt {attempt+1}/{max_retries}): {e}")

            # Exponential backoff: 0.5s, 1s, 2s
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                logger.debug(f"VisionDecoder retrying in {wait_time}s...")
                time.sleep(wait_time)

        logger.error("VisionDecoder REST API failed after all retries")
        return None

    def _try_credentials_api_with_retry(self, image_bytes: bytes, cache, max_retries: int = 2) -> List[Barcode]:
        """Try credentials API with retry."""
        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds:
            return None

        try:
            from google.cloud import vision  # type: ignore
        except Exception as e:
            logger.error(f"VisionDecoder: Failed to import google.cloud.vision: {e}")
            return None

        for attempt in range(max_retries):
            try:
                client = vision.ImageAnnotatorClient()
                gimg = vision.Image(content=image_bytes)
                resp = client.text_detection(image=gimg)

                if resp.error.message:
                    logger.warning(f"VisionDecoder credentials API error: {resp.error.message} (attempt {attempt+1}/{max_retries})")
                else:
                    barcodes = self._extract_barcodes(resp.full_text_annotation.text)
                    # Cache the result
                    cache.put(image_bytes, barcodes)
                    logger.debug(f"VisionDecoder credentials API success (attempt {attempt+1})")
                    return barcodes

            except Exception as e:
                logger.warning(f"VisionDecoder credentials API exception (attempt {attempt+1}/{max_retries}): {e}")

            # Exponential backoff: 0.5s, 1s
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                logger.debug(f"VisionDecoder retrying credentials API in {wait_time}s...")
                time.sleep(wait_time)

        logger.error("VisionDecoder credentials API failed after all retries")
        return None

    def _extract_barcodes(self, text: str) -> List[Barcode]:
        if not text:
            return []
        text = text.strip()
        digits = re.findall(r"\b(\d{8}|\d{12}|\d{13})\b", text)
        out: List[Barcode] = []
        seen = set()
        for d in digits:
            if d in seen:
                continue
            seen.add(d)
            out.append(Barcode(symbology="OCR", data=d, source=self.name))
        return out
