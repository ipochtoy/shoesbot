"""Helper to upload photo batches to Django."""
import os
import json
import base64
import aiohttp
from io import BytesIO
from PIL import Image
from shoesbot.logging_setup import logger
from shoesbot.photo_queue import PhotoUploadQueue


DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/photos/api/upload-batch/")

# Initialize photo queue
_photo_queue = PhotoUploadQueue()


async def upload_batch_to_django(
    correlation_id: str,
    chat_id: int,
    message_ids: list,
    photo_items: list,
    all_results: list,
) -> bool:
    """Upload photo batch to Django API with queue protection."""
    if not DJANGO_API_URL:
        return False
    
    try:
        photos_data = []
        for idx, item in enumerate(photo_items):
            # Download photo
            buf = BytesIO()
            await item.file_obj.download_to_memory(out=buf)
            raw = buf.getvalue()
            
            # Convert to base64
            img_b64 = base64.b64encode(raw).decode('utf-8')
            
            photos_data.append({
                'file_id': item.file_id,
                'message_id': item.message_id,
                'image': img_b64,
            })
        
        # Prepare barcodes
        barcodes_data = []
        for result in all_results:
            # Find which photo this barcode came from (simplified - assume first photo for now)
            barcodes_data.append({
                'photo_index': 0,  # TODO: track which photo each barcode came from
                'symbology': result.symbology,
                'data': result.data,
                'source': result.source,
            })
        
        # SAVE TO QUEUE FIRST (protection against Django crash)
        queue_id = _photo_queue.add_upload(
            correlation_id=correlation_id,
            chat_id=chat_id,
            message_ids=message_ids,
            photos_data=photos_data,
            barcodes_data=barcodes_data,
        )
        
        payload = {
            'correlation_id': correlation_id,
            'chat_id': chat_id,
            'message_ids': message_ids,
            'photos': photos_data,
            'barcodes': barcodes_data,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                DJANGO_API_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"django_upload: uploaded batch {correlation_id}: {result}")
                    
                    # SUCCESS - mark as uploaded in queue
                    _photo_queue.mark_uploaded(correlation_id)
                    
                    # Проверяем результат Pochtoy и отправляем в чат
                    pochtoy_msg = result.get('pochtoy_message')
                    if pochtoy_msg:
                        try:
                            # Используем requests синхронно (т.к. telegram-bot async сложнее)
                            import requests
                            bot_token = os.getenv('BOT_TOKEN')
                            telegram_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                            requests.post(telegram_url, json={
                                'chat_id': chat_id,
                                'text': f"📡 Pochtoy:\n{pochtoy_msg}"
                            }, timeout=5)
                            logger.info(f"Sent Pochtoy message to chat: {pochtoy_msg}")
                        except Exception as e:
                            logger.error(f"Failed to send Pochtoy message: {e}")
                    
                    return True
                else:
                    text = await resp.text()
                    error_msg = f"HTTP {resp.status}: {text[:200]}"
                    logger.warning(f"django_upload: failed {error_msg}")
                    
                    # Mark as failed for retry
                    _photo_queue.mark_failed(correlation_id, error_msg)
                    return False
                    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"django_upload: error: {error_msg}", exc_info=True)
        
        # Mark as failed for retry
        _photo_queue.mark_failed(correlation_id, error_msg)
        return False

