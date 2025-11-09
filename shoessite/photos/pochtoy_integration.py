"""Интеграция с Pochtoy API для отправки карточек товаров."""
import os
import base64
import requests
from typing import List, Dict, Optional


POCHTOY_API_URL = os.getenv('POCHTOY_API_URL', 'https://pochtoy-test.pochtoy3.ru/api/garage/store')
POCHTOY_API_TOKEN = os.getenv('POCHTOY_API_TOKEN', 'uqwyfg4367gqfuifg3')


def send_card_to_pochtoy(card) -> Optional[Dict]:
    """
    Отправляет карточку товара в Pochtoy API.
    
    Args:
        card: PhotoBatch объект
    
    Returns:
        Response dict или None при ошибке
    """
    try:
        # 1. Собираем все изображения
        images = []
        for idx, photo in enumerate(card.photos.all()):
            try:
                # Читаем файл
                with photo.image.open('rb') as f:
                    image_data = f.read()
                
                # Конвертим в base64
                img_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # Определяем имя файла
                filename = f"{card.correlation_id}_{idx}.jpg"
                
                images.append({
                    'base64': img_b64,
                    'file_name': filename
                })
                
            except Exception as e:
                print(f"Error encoding photo {photo.id}: {e}")
                continue
        
        # 2. Собираем все трекинги (GG лейблы + баркоды)
        trackings = []
        
        # GG лейблы
        gg_labels = card.get_gg_labels()
        trackings.extend(gg_labels)
        
        # Обычные баркоды
        barcodes = card.get_all_barcodes()
        for barcode in barcodes:
            if barcode.data not in trackings:
                trackings.append(barcode.data)
        
        # Удаляем дубликаты, сохраняя порядок
        trackings = list(dict.fromkeys(trackings))
        
        # 3. Формируем payload
        payload = {
            'images': images,
            'trackings': trackings
        }
        
        print(f"Sending to Pochtoy: {len(images)} images, {len(trackings)} trackings")
        
        # 4. Отправляем в Pochtoy API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POCHTOY_API_TOKEN}'
        }
        
        response = requests.put(
            POCHTOY_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        print(f"Pochtoy API response: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
            # Проверяем статус код
        if response.status_code == 400:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Неизвестная ошибка')
                return {
                    'success': False,
                    'error': error_msg
                }
            except:
                return {
                    'success': False,
                    'error': response.text[:200]
                }
        elif response.status_code in [200, 201, 202]:
            try:
                result = response.json()
                if result.get('status') == 'ok':
                    return {
                        'success': True,
                        'message': 'Товар успешно добавлен',
                        'images_sent': len(images),
                        'trackings_sent': len(trackings)
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Ошибка от Pochtoy')
                    }
            except:
                return {
                    'success': True,
                    'message': 'Товар успешно добавлен',
                    'images_sent': len(images),
                    'trackings_sent': len(trackings)
                }
        else:
            return {
                'success': False,
                'error': f'HTTP error: {response.status_code}',
                'response': response.text[:500]
            }
            
    except Exception as e:
        print(f"Error sending to Pochtoy: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def send_buffer_group_to_pochtoy(group_photos: List) -> Optional[Dict]:
    """
    Отправляет группу фото из буфера в Pochtoy API.
    
    Args:
        group_photos: QuerySet или список PhotoBuffer объектов
    
    Returns:
        Response dict
    """
    try:
        # Собираем изображения
        images = []
        for idx, photo in enumerate(group_photos):
            try:
                with photo.image.open('rb') as f:
                    image_data = f.read()
                
                img_b64 = base64.b64encode(image_data).decode('utf-8')
                filename = f"buffer_{photo.id}_{idx}.jpg"
                
                images.append({
                    'base64': img_b64,
                    'file_name': filename
                })
            except:
                continue
        
        # Собираем трекинги (GG лейблы из буфера)
        trackings = []
        for photo in group_photos:
            if photo.gg_label and photo.gg_label not in trackings:
                trackings.append(photo.gg_label)
            if photo.barcode and photo.barcode not in trackings:
                trackings.append(photo.barcode)
        
        # Удаляем дубликаты
        trackings = list(dict.fromkeys(trackings))
        
        # Отправляем
        payload = {
            'images': images,
            'trackings': trackings
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POCHTOY_API_TOKEN}'
        }
        
        response = requests.put(POCHTOY_API_URL, json=payload, headers=headers, timeout=60)
        
        print(f"Pochtoy response status: {response.status_code}")
        print(f"Pochtoy response body: {response.text}")
        
        # Проверяем статус код
        if response.status_code == 400:
            # Ошибка от Pochtoy
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Неизвестная ошибка')
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': 400
                }
            except:
                return {
                    'success': False,
                    'error': response.text[:200],
                    'status_code': 400
                }
        elif response.status_code in [200, 201, 202]:
            # Успех
            try:
                result = response.json()
                if result.get('status') == 'ok':
                    return {
                        'success': True,
                        'message': 'Товар успешно добавлен',
                        'images_sent': len(images),
                        'trackings_sent': len(trackings)
                    }
                else:
                    # Статус не ok
                    return {
                        'success': False,
                        'error': result.get('message', 'Неизвестная ошибка')
                    }
            except:
                # Если JSON невалидный, но статус 200 - считаем успехом
                return {
                    'success': True,
                    'message': 'Товар успешно добавлен',
                    'images_sent': len(images),
                    'trackings_sent': len(trackings)
                }
        else:
            return {
                'success': False,
                'error': f'HTTP error: {response.status_code}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def delete_from_pochtoy(trackings: List[str]) -> Dict:
    """
    Удаляет товар из Pochtoy по трекингам.
    
    Args:
        trackings: Список трекингов ["GG1100", "197613340718", ...]
    
    Returns:
        Result dict
    """
    try:
        POCHTOY_DELETE_URL = 'https://pochtoy-test.pochtoy3.ru/api/garage/delete'
        
        if not trackings:
            return {'success': False, 'error': 'No trackings'}
        
        trackings = list(dict.fromkeys(trackings))
        payload = {'trackings': trackings}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POCHTOY_API_TOKEN}'
        }
        
        print(f"Deleting from Pochtoy: {trackings}")
        
        # POST метод (не DELETE)
        response = requests.post(POCHTOY_DELETE_URL, json=payload, headers=headers, timeout=30)
        
        print(f"Pochtoy DELETE response: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 400:
            try:
                error_data = response.json()
                return {'success': False, 'error': error_data.get('message', 'Ошибка')}
            except:
                return {'success': False, 'error': response.text[:200]}
                
        elif response.status_code in [200, 201, 204]:
            try:
                result = response.json()
                if result.get('status') == 'ok':
                    return {'success': True, 'message': 'Удалено из Pochtoy'}
                else:
                    return {'success': False, 'error': result.get('message', 'Ошибка')}
            except:
                return {'success': True, 'message': 'Удалено из Pochtoy'}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        print(f"Pochtoy delete error: {e}")
        return {'success': False, 'error': str(e)}

