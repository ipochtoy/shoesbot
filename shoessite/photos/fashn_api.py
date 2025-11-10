"""FASHN AI API integration for Product to Model generation."""
import os
import sys
import requests
import time
from typing import Optional

# Загружаем .env
try:
    from dotenv import load_dotenv
    # Автоматически находим корень проекта (где находится .env)
    # fashn_api.py находится в shoessite/photos/, нужно подняться на 2 уровня вверх
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}", file=sys.stderr)
    else:
        print(f"⚠️ .env not found at: {env_path}", file=sys.stderr)
except ImportError:
    print("⚠️ python-dotenv not installed", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Error loading .env: {e}", file=sys.stderr)

FASHN_API_KEY = os.getenv('FASHN_API_KEY')
FASHN_API_URL = 'https://api.fashn.ai/v1'

# Проверка API ключа при импорте модуля
if FASHN_API_KEY:
    print(f"✅ FASHN_API_KEY loaded: ***{FASHN_API_KEY[-4:] if len(FASHN_API_KEY) > 4 else '****'}", file=sys.stderr)
else:
    print("⚠️ FASHN_API_KEY not set in .env", file=sys.stderr)


def generate_model_with_product(
    product_image_url: str,
    prompt: Optional[str] = None,
    resolution: str = '1k',
    aspect_ratio: Optional[str] = None
) -> Optional[str]:
    """
    Генерирует фото модели в одежде через FASHN AI Product to Model.
    
    Args:
        product_image_url: Публичный URL фото товара
        prompt: Текстовые инструкции ("professional studio photo", "man with tattoos")
        resolution: "1k" (точный) или "4k" (креативный HD)
        aspect_ratio: "1:1", "3:4", "9:16" и т.д. (опционально)
    
    Returns:
        URL сгенерированного изображения или None при ошибке
    """
    log_file = '/tmp/fashn_api.log'
    
    def log(msg):
        with open(log_file, 'a') as f:
            f.write(f"{msg}\n")
        print(msg, file=sys.stderr)
    
    log(f"\n{'='*70}")
    log(f"FASHN AI - Product to Model")
    log(f"{'='*70}")
    log(f"Image: {product_image_url}")
    log(f"Prompt: {prompt}")
    log(f"API Key: {'***' + FASHN_API_KEY[-4:] if FASHN_API_KEY else 'NOT SET'}")
    
    if not FASHN_API_KEY:
        log("❌ FASHN_API_KEY not set")
        return None
    
    try:
        # 1. Submit задачу
        log("\nStep 1: Submitting to FASHN API...")
        
        inputs = {
            'product_image': product_image_url,
            'output_format': 'jpeg',
            'resolution': resolution,
        }
        
        if prompt:
            inputs['prompt'] = prompt
        if aspect_ratio:
            inputs['aspect_ratio'] = aspect_ratio
        
        headers = {
            'Authorization': f'Bearer {FASHN_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model_name': 'product-to-model',
            'inputs': inputs
        }
        
        response = requests.post(
            f'{FASHN_API_URL}/run',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        log(f"Response status: {response.status_code}")
        log(f"Response: {response.text[:500]}")
        
        if response.status_code != 200:
            log(f"❌ Submit failed: {response.status_code}")
            return None
        
        result = response.json()
        if 'error' in result and result['error']:
            log(f"❌ Submit error: {result['error']}")
            return None
        
        prediction_id = result.get('id')
        if not prediction_id:
            log(f"❌ No prediction ID in response")
            return None
        
        log(f"✅ Prediction ID: {prediction_id}")
        
        # 2. Poll статус
        log("\nStep 2: Polling status...")
        max_attempts = 60  # 60 попыток * 2 сек = 2 минуты макс
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            time.sleep(2)
            
            status_resp = requests.get(
                f'{FASHN_API_URL}/status/{prediction_id}',
                headers=headers,
                timeout=10
            )
            
            if status_resp.status_code != 200:
                log(f"❌ Status check failed: {status_resp.status_code}")
                continue
            
            status_data = status_resp.json()
            status = status_data.get('status')
            
            log(f"Attempt {attempt}: status={status}")
            
            if status == 'completed':
                output = status_data.get('output')
                if output and len(output) > 0:
                    image_url = output[0]
                    log(f"✅ Completed! Result URL: {image_url}")
                    return image_url
                else:
                    log(f"❌ No output in completed response")
                    return None
                    
            elif status == 'failed':
                error = status_data.get('error', {})
                log(f"❌ Generation failed: {error}")
                return None
            
            # Status: pending or processing - continue polling
        
        log(f"❌ Timeout after {max_attempts} attempts")
        return None
        
    except Exception as e:
        log(f"❌ Exception: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def change_background(image_url: str, background_prompt: str = "studio background") -> Optional[str]:
    """
    Меняет фон через FASHN Background Change.
    
    Args:
        image_url: Публичный URL изображения
        background_prompt: Описание фона
    
    Returns:
        URL обработанного изображения
    """
    log_file = '/tmp/fashn_bg_change.log'
    
    def log(msg):
        with open(log_file, 'a') as f:
            f.write(f"{msg}\n")
        print(msg, file=sys.stderr)
    
    log(f"\n{'='*70}")
    log(f"FASHN Background Change")
    log(f"Image: {image_url}")
    log(f"Prompt: {background_prompt}")
    log(f"API Key: {'***' + FASHN_API_KEY[-4:] if FASHN_API_KEY else 'NOT SET'}")
    
    if not FASHN_API_KEY:
        log("❌ FASHN_API_KEY not set")
        return None
    
    try:
        log("\nStep 1: Submitting to FASHN API...")
        
        headers = {
            'Authorization': f'Bearer {FASHN_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            f'{FASHN_API_URL}/run',
            headers=headers,
            json={
                'model_name': 'background-change',
                'inputs': {
                    'image': image_url,
                    'prompt': background_prompt,
                    'output_format': 'jpeg'
                }
            },
            timeout=30
        )
        
        log(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            log(f"❌ Submit failed: {response.status_code}")
            log(f"Response: {response.text[:500]}")
            return None
        
        prediction_id = response.json().get('id')
        log(f"✅ Prediction ID: {prediction_id}")
        
        # Poll
        log("\nStep 2: Polling status...")
        for attempt in range(40):
            time.sleep(2)
            status_resp = requests.get(f'{FASHN_API_URL}/status/{prediction_id}', headers=headers, timeout=10)
            status = status_resp.json().get('status')
            
            log(f"Attempt {attempt + 1}: status={status}")
            
            if status == 'completed':
                output = status_resp.json().get('output', [])
                if output:
                    log(f"✅ Completed! Result URL: {output[0]}")
                    return output[0]
                log(f"❌ No output in completed response")
                return None
            elif status == 'failed':
                error = status_resp.json().get('error', {})
                log(f"❌ Failed: {error}")
                return None
        
        log("❌ Timeout after 40 attempts")
        return None
        
    except Exception as e:
        log(f"❌ Exception: {e}")
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

