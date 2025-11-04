"""
Улучшенный декодер для GG label detection.
Множественные стратегии для надежного чтения.
"""
from typing import List
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder
from shoesbot.logging_setup import logger
import re
import os
import base64


class ImprovedGGLabelDecoder(Decoder):
    """
    Улучшенный декодер с несколькими стратегиями:
    1. Множественные версии предобработанных изображений
    2. DOCUMENT_TEXT_DETECTION + TEXT_DETECTION
    3. Разные масштабы и контрасты
    4. Поиск по более гибким паттернам
    """
    name = "gg-label-improved"

    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        logger.debug("gg-label-improved: decode called")
        
        results = []
        seen = set()
        
        # Стратегия 1: Несколько версий изображения с разной обработкой
        image_variants = self._prepare_image_variants(image, image_bytes)
        
        api_key = os.getenv("GOOGLE_VISION_API_KEY")
        if not api_key:
            logger.warning("gg-label-improved: GOOGLE_VISION_API_KEY not set")
            return []
        
        # Пробуем каждую версию изображения
        for variant_name, variant_bytes in image_variants:
            logger.debug(f"gg-label-improved: Trying variant: {variant_name}")
            
            # Используем оба типа детекции
            variant_results = self._try_google_vision(variant_bytes, api_key, variant_name)
            
            for result in variant_results:
                key = (result.symbology, result.data)
                if key not in seen:
                    seen.add(key)
                    results.append(result)
            
            # Если нашли в первой версии - можем вернуться быстрее
            if results and variant_name == "high_contrast":
                logger.info(f"gg-label-improved: Found codes early with {variant_name}: {[b.data for b in results]}")
                return results
        
        logger.info(f"gg-label-improved: Final results: {[b.data for b in results]}")
        return results
    
    def _prepare_image_variants(self, image: Image.Image, image_bytes: bytes) -> List[tuple]:
        """Создает несколько версий изображения с разной обработкой."""
        variants = []
        
        try:
            # Вариант 1: Высокий контраст и резкость (для желтых стикеров)
            proc1 = image.copy()
            if proc1.width < 2000:
                ratio = 2000 / float(proc1.width)
                proc1 = proc1.resize((int(proc1.width * ratio), int(proc1.height * ratio)), Image.LANCZOS)
            proc1 = ImageEnhance.Contrast(proc1).enhance(2.0)  # Агрессивный контраст
            proc1 = ImageEnhance.Sharpness(proc1).enhance(1.5)
            buf1 = BytesIO()
            proc1.save(buf1, format="PNG")
            variants.append(("high_contrast", buf1.getvalue()))
            
            # Вариант 2: Увеличенное разрешение, умеренный контраст
            proc2 = image.copy()
            if proc2.width < 2400:
                ratio = 2400 / float(proc2.width)
                proc2 = proc2.resize((int(proc2.width * ratio), int(proc2.height * ratio)), Image.LANCZOS)
            proc2 = ImageEnhance.Contrast(proc2).enhance(1.5)
            buf2 = BytesIO()
            proc2.save(buf2, format="PNG")
            variants.append(("high_res", buf2.getvalue()))
            
            # Вариант 3: Оригинал с легкой обработкой (fallback)
            proc3 = image.copy()
            if proc3.width < 1600:
                ratio = 1600 / float(proc3.width)
                proc3 = proc3.resize((int(proc3.width * ratio), int(proc3.height * ratio)), Image.BICUBIC)
            proc3 = ImageEnhance.Contrast(proc3).enhance(1.3)
            buf3 = BytesIO()
            proc3.save(buf3, format="PNG")
            variants.append(("standard", buf3.getvalue()))
            
        except Exception as e:
            logger.debug(f"gg-label-improved: Error preparing variants: {e}")
            # Fallback на оригинал
            variants.append(("original", image_bytes))
        
        return variants
    
    def _try_google_vision(self, image_bytes: bytes, api_key: str, variant_name: str) -> List[Barcode]:
        """Пробует Google Vision API с разными типами детекции."""
        results = []
        
        try:
            import requests
            img_b64 = base64.b64encode(image_bytes).decode()
            url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
            
            # Пробуем DOCUMENT_TEXT_DETECTION (лучше для документов/стикеров)
            payload_doc = {
                "requests": [{
                    "image": {"content": img_b64},
                    "features": [
                        {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                    ],
                    "imageContext": {
                        "languageHints": ["en"]
                    }
                }]
            }
            
            resp = requests.post(url, json=payload_doc, timeout=12)
            if resp.ok:
                data = resp.json()
                if "responses" in data and data["responses"]:
                    text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                    if text:
                        logger.debug(f"gg-label-improved: DOCUMENT_TEXT_DETECTION ({variant_name}) found {len(text)} chars")
                        doc_results = self._extract_gg_labels(text, f"{self.name}-doc-{variant_name}")
                        results.extend(doc_results)
            
            # Если не нашли, пробуем TEXT_DETECTION
            if not results:
                payload_text = {
                    "requests": [{
                        "image": {"content": img_b64},
                        "features": [
                            {"type": "TEXT_DETECTION", "maxResults": 10}
                        ],
                        "imageContext": {
                            "languageHints": ["en"]
                        }
                    }]
                }
                
                resp = requests.post(url, json=payload_text, timeout=12)
                if resp.ok:
                    data = resp.json()
                    if "responses" in data and data["responses"]:
                        text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
                        if text:
                            logger.debug(f"gg-label-improved: TEXT_DETECTION ({variant_name}) found {len(text)} chars")
                            text_results = self._extract_gg_labels(text, f"{self.name}-text-{variant_name}")
                            results.extend(text_results)
            
        except Exception as e:
            logger.debug(f"gg-label-improved: Google Vision error ({variant_name}): {e}")
        
        return results
    
    def _extract_gg_labels(self, text: str, source: str = None) -> List[Barcode]:
        """Извлекает GG коды из текста с улучшенными паттернами."""
        if not text:
            return []
        
        text = text.strip()
        source = source or self.name
        
        # Улучшенные паттерны - учитываем ошибки OCR
        patterns = [
            # Точные совпадения
            r'\bGG[-.\s]?(\d{2,4})\b',
            r'\bG(\d{3,4})\b',
            # Ошибки OCR: O вместо G, 6 вместо G
            r'\bOO[-.\s]?(\d{2,4})\b',  # OO747 -> GG747
            r'\b66[-.\s]?(\d{2,4})\b',  # 66747 -> GG747
            r'\b[GO6]{2}[-.\s]?(\d{2,4})\b',  # Любая комбинация
            # Просто цифры 747, 752, 753 (типичные GG коды)
            r'\b(747|752|753|754|755|756|757|758|759|760)\b',
        ]
        
        out = []
        seen = set()
        
        # Сначала ищем точные совпадения
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    num = match[0] if match[0] else ''
                else:
                    num = match
                
                if num and num.isdigit():
                    # Определяем формат
                    if 'OO' in pattern or '66' in pattern or '[GO6]' in pattern:
                        label = f"GG{num}"
                    elif 'G(\d' in pattern:
                        label = f"G{num}"
                    elif 'GG' in pattern:
                        label = f"GG{num}"
                    else:
                        # Просто цифры - проверяем контекст
                        # Ищем есть ли G/O/6 рядом
                        num_pos = text.find(num)
                        if num_pos > 0:
                            context = text[max(0, num_pos-3):num_pos+len(num)+3]
                            if re.search(r'[GO6]{1,2}', context, re.IGNORECASE):
                                label = f"GG{num}"
                            else:
                                continue
                        else:
                            continue
                    
                    if label not in seen:
                        seen.add(label)
                        out.append(Barcode(symbology="CODE39", data=label, source=source))
        
        if out:
            logger.debug(f"gg-label-improved: extracted labels: {[b.data for b in out]}")
        
        return out

