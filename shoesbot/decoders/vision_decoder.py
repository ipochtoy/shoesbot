from typing import List
import os
import re
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

class VisionDecoder(Decoder):
    name = "vision-ocr"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds:
            return []
        try:
            from google.cloud import vision  # type: ignore
        except Exception:
            return []
        client = vision.ImageAnnotatorClient()
        gimg = vision.Image(content=image_bytes)
        resp = client.text_detection(image=gimg)
        if resp.error.message:
            return []
        text = (resp.full_text_annotation.text or "").strip()
        digits = re.findall(r"\b(\d{8}|\d{12}|\d{13})\b", text)
        out: List[Barcode] = []
        seen = set()
        for d in digits:
            if d in seen:
                continue
            seen.add(d)
            out.append(Barcode(symbology="OCR", data=d, source=self.name))
        return out
