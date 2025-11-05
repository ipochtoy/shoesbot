"""OpenAI Vision decoder для чтения баркодов с коробок."""
import os
import base64
import requests
from typing import List
from PIL import Image
from shoesbot.models import Barcode
from shoesbot.decoders.base import Decoder


class OpenAIBarcodeDecoder(Decoder):
    name = "openai-barcode"
    
    def decode(self, image: Image.Image, image_bytes: bytes) -> List[Barcode]:
        """Использует OpenAI Vision для чтения баркодов на коробках."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return []
        
        try:
            # Конвертим в base64
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': '''Find and extract ALL barcodes/UPC codes visible on this image.
Look for:
- Long numeric codes (12-14 digits) under barcodes
- UPC/EAN numbers on product boxes
- Any visible numeric codes

Return ONLY the numbers, one per line, no additional text.
Example:
197613340718
012345678901'''
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{img_b64}'
                            }
                        }
                    ]
                }],
                'max_tokens': 150,
                'temperature': 0.1  # Низкая температура для точности
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            # Парсим результат - ищем все числа 12-14 цифр
            results = []
            seen = set()
            
            for line in text.split('\n'):
                # Убираем лишнее и оставляем только цифры
                digits = ''.join(c for c in line if c.isdigit())
                
                # Баркоды обычно 12-14 цифр
                if 12 <= len(digits) <= 14 and digits not in seen:
                    seen.add(digits)
                    
                    # Определяем тип по длине
                    if len(digits) == 13:
                        symbology = 'EAN13'
                    elif len(digits) == 12:
                        symbology = 'UPCA'
                    else:
                        symbology = 'CODE128'
                    
                    results.append(Barcode(
                        symbology=symbology,
                        data=digits,
                        source='openai-barcode'
                    ))
            
            return results
            
        except Exception as e:
            print(f"OpenAI barcode decoder error: {e}")
            return []

