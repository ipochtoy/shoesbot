from typing import List
import os
import re
import base64
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder

class VisionDecoder(Decoder):
    name = "vision-ocr"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        # Try REST API with API key first
        api_key = os.getenv("GOOGLE_VISION_API_KEY")
        if api_key:
            try:
                import requests
                img_b64 = base64.b64encode(image_bytes).decode()
                url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
                payload = {
                    "requests": [{
                        "image": {"content": img_b64},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }]
                }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.ok:
                    data = resp.json()
                    if "responses" in data and data["responses"]:
                        text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                        return self._extract_barcodes(text)
            except Exception:
                pass
        
        # Fallback to credentials JSON file
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
        return self._extract_barcodes(resp.full_text_annotation.text)
    
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
