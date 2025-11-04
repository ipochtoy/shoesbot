"""Decoder for GG label detection via OCR."""
from typing import List
from PIL import Image
from io import BytesIO
from PIL import ImageEnhance
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder
from shoesbot.logging_setup import logger
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
        logger.debug("gg-label: decode called")
        # Preprocess: upscale small images and boost contrast for better OCR
        try:
            proc_img = image
            max_w = 1600
            if image.width < max_w:
                ratio = max_w / float(image.width)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                proc_img = image.resize(new_size, Image.BICUBIC)
            # Light contrast boost
            proc_img = ImageEnhance.Contrast(proc_img).enhance(1.3)
            buf = BytesIO()
            proc_img.save(buf, format="PNG")
            proc_bytes = buf.getvalue()
        except Exception:
            proc_bytes = image_bytes
        # Try REST API with API key first
        api_key = os.getenv("GOOGLE_VISION_API_KEY")
        logger.debug(f"gg-label: API key present: {api_key is not None}")
        if api_key:
            try:
                import requests
                img_b64 = base64.b64encode(proc_bytes).decode()
                url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
                payload = {
                    "requests": [{
                        "image": {"content": img_b64},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }]
                }
                resp = requests.post(url, json=payload, timeout=8)  # Баланс между скоростью и надежностью
                logger.info(f"gg-label: Vision REST status={resp.status_code}")
                if resp.ok:
                    data = resp.json()
                    if "responses" in data and data["responses"]:
                        text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                        logger.info(f"gg-label: Vision REST text_len={len(text)}")
                        if text:
                            logger.debug(f"gg-label: Vision API text preview: {text[:200]}")
                        results = self._extract_gg_labels(text)
                        logger.info(f"gg-label: REST extracted {len(results)} labels")
                        return results
                else:
                    try:
                        logger.info(f"gg-label: Vision REST error body: {resp.text[:200]}")
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"gg-label: Vision API error: {e}")
                pass
        
        # Fallback to credentials file
        if not HAS_VISION:
            return []
        
        try:
            client = vision.ImageAnnotatorClient()
            gimg = vision.Image(content=proc_bytes)
            resp = client.text_detection(image=gimg)
            
            if resp.error.message:
                return []
            
            text = (resp.full_text_annotation.text or "").strip()
            logger.info(f"gg-label: Vision client text_len={len(text)}")
            if text:
                logger.debug(f"gg-label: Vision client text preview: {text[:200]}")
            results = self._extract_gg_labels(text)
            logger.info(f"gg-label: client extracted {len(results)} labels")
            return results
        except Exception as e:
            logger.debug(f"gg-label: Vision client error: {e}")
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
        
        if out:
            logger.debug(f"gg-label: found labels: {[b.data for b in out]}")
        
        return out

