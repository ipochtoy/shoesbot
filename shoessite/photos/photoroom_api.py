"""Photoroom API integration for product photo enhancement."""
import os
import requests
from typing import Optional


PHOTOROOM_API_KEY = os.getenv('PHOTOROOM_API_KEY', 'sandbox_sk_pr_default_973d09b50f67c7232b1b0ba956a5cf2990f020d0')


def enhance_product_photo(image_path: str, mode: str = 'ghost_mannequin') -> Optional[bytes]:
    """
    Обработка фото товара через Photoroom API v2.
    
    Args:
        image_path: Путь к изображению
        mode: 'ghost_mannequin' (убрать фон + тени) или 'product_beautifier' (улучшить фото)
    
    Returns:
        Обработанное изображение в байтах или None при ошибке
    """
    if not PHOTOROOM_API_KEY:
        print("PHOTOROOM_API_KEY not set")
        return None
    
    try:
        # Читаем изображение
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Photoroom API v2 - Image Editing endpoint
        url = 'https://image-api.photoroom.com/v2/edit'
        
        headers = {
            'x-api-key': PHOTOROOM_API_KEY,
            'Accept': 'image/png, application/json',
        }
        
        files = {
            'imageFile': ('product.jpg', image_data, 'image/jpeg')
        }
        
        # Параметры в зависимости от режима
        if mode == 'ghost_mannequin':
            # Remove background + hard shadows (имитация манекена)
            params = {
                'removeBackground': 'true',
                'background.color': 'ffffff',
                'shadow.mode': 'ai.hard',  # Жесткая тень
                'padding': '0.1',
                'export.format': 'png',
                'outputSize': '2000x2000',
            }
        else:  # product_beautifier
            # AI улучшение товара
            params = {
                'beautify.mode': 'ai.auto',
                'removeBackground': 'true',
                'background.color': 'ffffff',
                'shadow.mode': 'ai.soft',
                'padding': '0.05',
                'export.format': 'jpg',
                'outputSize': '2000x2000',
            }
        
        print(f"Sending photo to Photoroom API v2 (mode: {mode})...")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=params,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Photoroom API success, received {len(response.content)} bytes")
            return response.content
        else:
            print(f"❌ Photoroom API error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"Error in enhance_product_photo: {e}")
        import traceback
        traceback.print_exc()
        return None
