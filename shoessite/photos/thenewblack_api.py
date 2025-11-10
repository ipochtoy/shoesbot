"""The New Black AI API integration for ghost mannequin effect."""
import os
import requests
from typing import Optional
import time
import base64

# Загружаем .env
try:
    from dotenv import load_dotenv
    import sys
    # Автоматически находим корень проекта (где находится .env)
    # thenewblack_api.py находится в shoessite/photos/, нужно подняться на 2 уровня вверх
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}", file=sys.stderr)
    else:
        print(f"⚠️ .env not found at: {env_path}", file=sys.stderr)
except ImportError:
    import sys
    print("⚠️ python-dotenv not installed", file=sys.stderr)
except Exception as e:
    import sys
    print(f"⚠️ Error loading .env: {e}", file=sys.stderr)

TNB_EMAIL = os.getenv('TNB_EMAIL')
TNB_PASSWORD = os.getenv('TNB_PASSWORD')
TNB_API_URL = 'https://thenewblack.ai/api/1.1/wf/image_to_ghost'  # Подчеркивание, не дефис!
IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID', 'a42d0c09bb465d3')  # Анонимный upload


def upload_to_imgur(image_path: str) -> Optional[str]:
    """Загружает фото на Imgur и возвращает публичный URL."""
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}',
        }
        
        data = {
            'image': image_data,
            'type': 'base64',
        }
        
        print(f"📤 Uploading to Imgur...")
        response = requests.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('data'):
                url = result['data'].get('link')
                print(f"✅ Imgur upload success: {url}")
                return url
        else:
            print(f"❌ Imgur error: {response.status_code}")
            print(f"Response: {response.text[:300]}")
        
        return None
        
    except Exception as e:
        print(f"Error uploading to Imgur: {e}")
        return None


def create_ghost_mannequin_from_path(image_path: str, clothing_type: str = 'clothing') -> Optional[str]:
    """
    Создает эффект ghost mannequin из локального файла.
    Сначала загружает фото на Imgur, потом отправляет в The New Black.
    
    Args:
        image_path: Путь к локальному файлу
        clothing_type: Тип одежды
    
    Returns:
        URL обработанного изображения
    """
    # Загружаем на Imgur чтобы получить публичный URL
    public_url = upload_to_imgur(image_path)
    if not public_url:
        print("❌ Failed to upload to Imgur")
        return None
    
    # Теперь отправляем в The New Black
    return create_ghost_mannequin(public_url, clothing_type)


def create_ghost_mannequin(image_url: str, clothing_type: str = 'clothing') -> Optional[str]:
    """
    Создает эффект ghost mannequin через The New Black AI API.
    
    Args:
        image_url: URL изображения (должен быть доступен публично)
        clothing_type: Тип одежды ('dress', 'pants', 'shirt', 'jacket', 'sweater' и т.д.)
    
    Returns:
        URL обработанного изображения или None при ошибке
    """
    log_file = '/tmp/thenewblack_api.log'
    
    def log(msg):
        with open(log_file, 'a') as f:
            f.write(f"{msg}\n")
        print(msg)
    
    log(f"\n=== create_ghost_mannequin called ===")
    log(f"Image URL: {image_url}")
    log(f"Clothing type: {clothing_type}")
    log(f"TNB_EMAIL: {TNB_EMAIL}")
    log(f"TNB_PASSWORD: {'***' if TNB_PASSWORD else 'NOT SET'}")
    
    if not TNB_EMAIL or not TNB_PASSWORD:
        log("❌ TNB_EMAIL or TNB_PASSWORD not set")
        return None
    
    try:
        # Формируем запрос
        data = {
            'email': TNB_EMAIL,
            'password': TNB_PASSWORD,
            'image': image_url,
            'type': clothing_type,
        }
        
        log(f"Sending POST to: {TNB_API_URL}")
        log(f"Data: email={TNB_EMAIL}, image={image_url[:50]}..., type={clothing_type}")
        
        response = requests.post(
            TNB_API_URL,
            data=data,
            timeout=60
        )
        
        log(f"Response status: {response.status_code}")
        log(f"Response headers: {dict(response.headers)}")
        log(f"Response text (first 500 chars): {response.text[:500]}")
        log(f"Response content length: {len(response.content)}")
        
        if response.status_code == 200:
            # Проверяем что ответ не пустой
            if not response.text or not response.text.strip():
                log("❌ Response is empty")
                return None
            
            try:
                result = response.json()
                log(f"Response JSON: {result}")
            except Exception as json_err:
                log(f"❌ Failed to parse JSON: {json_err}")
                log(f"Response text: {response.text}")
                return None
            
            # API возвращает URL обработанного изображения
            if 'response' in result:
                result_image_url = result['response'].get('image_url')
                if result_image_url:
                    log(f"✅ Ghost mannequin URL: {result_image_url}")
                    return result_image_url
                else:
                    log(f"❌ No image_url in response: {result}")
                    return None
            else:
                log(f"❌ No 'response' key in result: {result}")
                return None
        else:
            log(f"❌ API error: {response.status_code}")
            log(f"Response text: {response.text[:500]}")
            return None
            
    except Exception as e:
        log(f"❌ Exception: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def download_image_from_url(url: str) -> Optional[bytes]:
    """Скачивает изображение по URL."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

