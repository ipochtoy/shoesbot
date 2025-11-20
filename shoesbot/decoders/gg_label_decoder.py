"""Decoder for GG label detection via OCR."""
from typing import List
from PIL import Image
from io import BytesIO
from PIL import ImageEnhance, ImageOps, ImageFilter
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
        variants = self._build_variants(image)
        api_key = os.getenv("GOOGLE_VISION_API_KEY")
        if api_key:
            for idx, variant in enumerate(variants):
                proc_bytes = variant["bytes"]
                text = self._call_vision_rest(proc_bytes, api_key, variant_idx=idx, feature_type="DOCUMENT_TEXT_DETECTION")
                if not text:
                    text = self._call_vision_rest(proc_bytes, api_key, variant_idx=idx, feature_type="TEXT_DETECTION")
                if text:
                    results = self._extract_gg_labels(text)
                    logger.info(f"gg-label: REST extracted {len(results)} labels (variant={idx})")
                    if results:
                        return results
        
        if HAS_VISION:
            for idx, variant in enumerate(variants):
                results = self._call_vision_client(variant["bytes"], variant_idx=idx)
                if results:
                    return results
        
        for idx, variant in enumerate(variants):
            text = self._local_ocr(variant["image"], idx)
            if text:
                results = self._extract_gg_labels(text)
                if results:
                    logger.info(f"gg-label: Tesseract extracted {len(results)} labels variant={idx}")
                    return results
        
        logger.info("gg-label: Vision failed to detect GG/Q labels, falling back to OpenAI")
        return []
    
    def _build_variants(self, image: Image.Image):
        variants = []
        image = image.convert("RGB")
        cropped = self._crop_yellow_patch(image)
        candidates = []
        if cropped:
            candidates.append(cropped)
        candidates.append(image)
        
        for candidate in candidates:
            proc = self._preprocess(candidate)
            variants.extend(self._variant_dicts(proc))
            rot90 = proc.rotate(90, expand=True)
            rot270 = proc.rotate(-90, expand=True)
            variants.extend(self._variant_dicts(rot90))
            variants.extend(self._variant_dicts(rot270))
        return variants
    
    def _variant_dicts(self, img: Image.Image):
        buf = BytesIO()
        img.save(buf, format="PNG")
        return [{
            "image": img,
            "bytes": buf.getvalue(),
        }]
    
    def _preprocess(self, image: Image.Image):
        max_w = 1400
        proc = image
        if proc.width < max_w:
            ratio = max_w / float(proc.width)
            proc = proc.resize((int(proc.width * ratio), int(proc.height * ratio)), Image.BICUBIC)
        proc = ImageEnhance.Contrast(proc).enhance(1.7)
        proc = ImageOps.autocontrast(proc)
        proc = proc.filter(ImageFilter.SHARPEN)
        return proc
    
    def _crop_yellow_patch(self, image: Image.Image):
        try:
            import cv2
            import numpy as np
            arr = image.convert("RGB")
            np_img = np.array(arr)
            hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)
            lower = np.array([18, 60, 120])
            upper = np.array([42, 255, 255])
            mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None
            contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < 3000:
                return None
            pad = 20
            x = max(0, x - pad)
            y = max(0, y - pad)
            x2 = min(np_img.shape[1], x + w + pad)
            y2 = min(np_img.shape[0], y + h + pad)
            cropped = np_img[y:y2, x:x2]
            return Image.fromarray(cropped)
        except Exception:
            return None
    
    def _call_vision_rest(self, proc_bytes: bytes, api_key: str, variant_idx: int, feature_type: str):
        try:
            import requests
            img_b64 = base64.b64encode(proc_bytes).decode()
            url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
            payload = {
                "requests": [{
                    "image": {"content": img_b64},
                    "features": [{"type": feature_type}],
                    "imageContext": {"languageHints": ["en", "ru", "zh"]},
                }]
            }
            resp = requests.post(url, json=payload, timeout=8)
            logger.info(f"gg-label: Vision REST status={resp.status_code} feature={feature_type} variant={variant_idx}")
            if resp.ok:
                data = resp.json()
                if "responses" in data and data["responses"]:
                    text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                    logger.info(f"gg-label: Vision REST text_len={len(text)} feature={feature_type} variant={variant_idx}")
                    if text:
                        logger.debug(f"gg-label: Vision REST text preview: {text[:200]}")
                    return text
            else:
                logger.info(f"gg-label: Vision REST error body: {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"gg-label: Vision REST error: {e}")
        return ""
    
    def _call_vision_client(self, proc_bytes: bytes, variant_idx: int):
        try:
            client = vision.ImageAnnotatorClient()
            gimg = vision.Image(content=proc_bytes)
            resp = client.document_text_detection(image=gimg, image_context={"language_hints": ["en"]})
            if resp.error.message:
                logger.info(f"gg-label: Vision client error message: {resp.error.message}")
                return []
            text = (resp.full_text_annotation.text or "").strip()
            logger.info(f"gg-label: Vision client text_len={len(text)} variant={variant_idx}")
            if text:
                logger.debug(f"gg-label: Vision client text preview: {text[:200]}")
            results = self._extract_gg_labels(text)
            logger.info(f"gg-label: client extracted {len(results)} labels variant={variant_idx}")
            return results
        except Exception as e:
            logger.debug(f"gg-label: Vision client error: {e}")
            return []
    
    def _local_ocr(self, image: Image.Image, variant_idx: int):
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, config="--psm 6")
            logger.info(f"gg-label: tesseract text_len={len(text)} variant={variant_idx}")
            if text:
                logger.debug(f"gg-label: tesseract text preview: {text[:200]}")
            return text
        except Exception as e:
            logger.debug(f"gg-label: tesseract error: {e}")
            return ""
    
    def _extract_gg_labels(self, text: str) -> List[Barcode]:
        if not text:
            return []
        text = text.strip()
        
        # Find GG patterns (GG followed by digits) OR G followed by 4 digits (like G2548)
        gg_pattern = re.compile(r'\bGG[-.\s]?(\d{2,7})\b', re.IGNORECASE)
        g_pattern = re.compile(r'\bG(\d{4})\b', re.IGNORECASE)
        q_pattern = re.compile(r'\bQ[-.\s]?(\d{4,10})\b', re.IGNORECASE)
        
        out = []
        seen = set()
        
        def add_label(prefix: str, value: str):
            label = f"{prefix}{value}".upper()
            if label in seen:
                return
            seen.add(label)
            out.append(Barcode(symbology="GG_LABEL", data=label, source=self.name))
        
        for match in gg_pattern.findall(text):
            add_label("GG", match)
        
        for match in g_pattern.findall(text):
            add_label("G", match)
        
        for match in q_pattern.findall(text):
            add_label("Q", match)
        
        if out:
            logger.debug(f"gg-label: found labels: {[b.data for b in out]}")
        
        return out

