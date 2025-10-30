"""Decoder for GG label detection via OCR."""
from typing import List
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder
import re

# OCR via Vision or pyzbar text_detection
try:
    import shoesbot.env_setup  # setup env
    from google.cloud import vision
    HAS_VISION = True
except Exception:
    HAS_VISION = False


class GGLabelDecoder(Decoder):
    name = "gg-label"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        if not HAS_VISION:
            return []
        
        # Detect GG label pattern (GG + numbers, e.g. GG765, GG-100, GG 42)
        try:
            client = vision.ImageAnnotatorClient()
            gimg = vision.Image(content=image_bytes)
            resp = client.text_detection(image=gimg)
            
            if resp.error.message:
                return []
            
            text = (resp.full_text_annotation.text or "").strip()
            if not text:
                return []
            
            # Find GG patterns (GG followed by digits)
            gg_pattern = re.compile(r'\bGG[-.\s]?(\d+)\b', re.IGNORECASE)
            matches = gg_pattern.findall(text)
            
            out = []
            seen = set()
            for num in matches:
                if num in seen:
                    continue
                seen.add(num)
                out.append(Barcode(symbology="GG", data=f"GG{num}", source=self.name))
            
            return out
        except Exception:
            return []

