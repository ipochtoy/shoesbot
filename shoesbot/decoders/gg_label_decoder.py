"""Decoder for GG label detection via OCR."""
from typing import List
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder
import re
import os
import base64

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
                        return self._extract_gg_labels(text)
            except Exception:
                pass
        
        # Fallback to credentials file
        if not HAS_VISION:
            return []
        
        try:
            client = vision.ImageAnnotatorClient()
            gimg = vision.Image(content=image_bytes)
            resp = client.text_detection(image=gimg)
            
            if resp.error.message:
                return []
            
            text = (resp.full_text_annotation.text or "").strip()
            return self._extract_gg_labels(text)
        except Exception:
            return []
    
    def _extract_gg_labels(self, text: str) -> List[Barcode]:
        if not text:
            return []
        text = text.strip()
        
        # Find GG patterns (GG followed by digits) OR G followed by 4 digits (like G2548)
        gg_pattern = re.compile(r'\b(GG[-.\s]?(\d+)|G(\d{4}))\b', re.IGNORECASE)
        matches = gg_pattern.findall(text)
        
        out = []
        seen = set()
        for match in matches:
            # match format: (full_match, GG_num, G_num)
            if match[1]:  # GG pattern matched
                num = match[1]
                label = f"GG{num}"
            elif match[2]:  # G + 4 digits pattern matched
                num = match[2]
                label = f"G{num}"
            else:
                continue
            
            if label in seen:
                continue
            seen.add(label)
            out.append(Barcode(symbology="GG", data=label, source=self.name))
        
        return out

