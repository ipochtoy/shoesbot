"""Helper to upload photo batches to Django."""
import os
import json
import base64
import asyncio
import sqlite3
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
        
        # Retry logic for Django connection
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
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
                            
                            # Retry on 5xx errors or connection issues
                            if resp.status >= 500 and attempt < max_retries - 1:
                                logger.warning(f"django_upload: attempt {attempt+1}/{max_retries} failed {error_msg}, retrying...")
                                await asyncio.sleep(retry_delay)
                                continue
                            
                            logger.warning(f"django_upload: failed {error_msg}")
                            _photo_queue.mark_failed(correlation_id, error_msg)
                            return False
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"django_upload: attempt {attempt+1}/{max_retries} connection error: {error_msg}, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"django_upload: error after {max_retries} attempts: {error_msg}", exc_info=True)
                    _photo_queue.mark_failed(correlation_id, error_msg)
                    return False
                    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"django_upload: error: {error_msg}", exc_info=True)
        
        # Mark as failed for retry
        _photo_queue.mark_failed(correlation_id, error_msg)
        return False


async def retry_upload_from_queue(correlation_id: str) -> bool:
    """
    Retry upload from queue using saved data.
    Used when user clicks "Retry" button.
    """
    if not DJANGO_API_URL:
        return False
    
    try:
        # Get data from queue
        conn = sqlite3.connect(_photo_queue.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chat_id, message_ids, photos_data, barcodes_data
            FROM pending_uploads
            WHERE correlation_id = ?
            ORDER BY id DESC
            LIMIT 1
        ''', (correlation_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logger.warning(f"retry_upload_from_queue: no data found for {correlation_id}")
            return False
        
        chat_id, message_ids_json, photos_data_json, barcodes_data_json = row
        message_ids = json.loads(message_ids_json)
        photos_data = json.loads(photos_data_json)
        barcodes_data = json.loads(barcodes_data_json)
        
        # Prepare payload (photos_data already has base64 images)
        payload = {
            'correlation_id': correlation_id,
            'chat_id': chat_id,
            'message_ids': message_ids,
            'photos': photos_data,
            'barcodes': barcodes_data,
        }
        
        # Retry logic
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        DJANGO_API_URL,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            logger.info(f"retry_upload_from_queue: uploaded batch {correlation_id}: {result}")
                            
                            # SUCCESS - mark as uploaded
                            _photo_queue.mark_uploaded(correlation_id)
                            
                            # Send Pochtoy message if present
                            pochtoy_msg = result.get('pochtoy_message')
                            if pochtoy_msg:
                                try:
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
                            
                            if resp.status >= 500 and attempt < max_retries - 1:
                                logger.warning(f"retry_upload_from_queue: attempt {attempt+1}/{max_retries} failed {error_msg}, retrying...")
                                await asyncio.sleep(retry_delay)
                                continue
                            
                            logger.warning(f"retry_upload_from_queue: failed {error_msg}")
                            _photo_queue.mark_failed(correlation_id, error_msg)
                            return False
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"retry_upload_from_queue: attempt {attempt+1}/{max_retries} connection error: {error_msg}, retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"retry_upload_from_queue: error after {max_retries} attempts: {error_msg}", exc_info=True)
                    _photo_queue.mark_failed(correlation_id, error_msg)
                    return False
                    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"retry_upload_from_queue: error: {error_msg}", exc_info=True)
        _photo_queue.mark_failed(correlation_id, error_msg)
        return False
    
    return False

