"""Helper to upload photo batches to Django."""
import os
import json
import asyncio
import sqlite3
import aiohttp
from typing import Optional, Tuple
from shoesbot.logging_setup import logger
from shoesbot.photo_queue import PhotoUploadQueue


DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/photos/api/upload-batch/")

# Initialize photo queue
_photo_queue = PhotoUploadQueue()


async def upload_batch_to_django(
    correlation_id: str,
    chat_id: int,
    message_ids: list,
    photos_data: list,
    barcodes_data: list,
) -> Tuple[bool, Optional[dict]]:
    """Upload photo batch to Django API with queue protection."""
    if not DJANGO_API_URL:
        return False, None
    if os.getenv("BENCHMARK_MODE") == "1":
        return True, {"benchmark": True}
    
    try:
        _photo_queue.add_upload(
            correlation_id=correlation_id,
            chat_id=chat_id,
            message_ids=message_ids,
            photos_data=photos_data,
            barcodes_data=barcodes_data,
        )
        _photo_queue.mark_in_progress(correlation_id)
        
        payload = {
            'correlation_id': correlation_id,
            'chat_id': chat_id,
            'message_ids': message_ids,
            'photos': photos_data,
            'barcodes': barcodes_data,
        }
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    async with session.post(
                        DJANGO_API_URL,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            logger.info(f"django_upload: uploaded batch {correlation_id}: {result}")
                            _photo_queue.mark_uploaded(correlation_id)
                            return True, result
                        
                        text = await resp.text()
                        error_msg = f"HTTP {resp.status}: {text[:200]}"
                        
                        if resp.status >= 500 and attempt < max_retries - 1:
                            logger.warning(f"django_upload: attempt {attempt+1}/{max_retries} failed {error_msg}, retrying...")
                            await asyncio.sleep(retry_delay)
                            continue
                        
                        logger.warning(f"django_upload: failed {error_msg}")
                        _photo_queue.mark_failed(correlation_id, error_msg)
                        return False, {'error': error_msg}
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    error_msg = str(e)
                    if attempt < max_retries - 1:
                        logger.warning(f"django_upload: attempt {attempt+1}/{max_retries} connection error: {error_msg}, retrying...")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.error(f"django_upload: error after {max_retries} attempts: {error_msg}", exc_info=True)
                    _photo_queue.mark_failed(correlation_id, error_msg)
                    return False, {'error': error_msg}
                    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"django_upload: error: {error_msg}", exc_info=True)
        _photo_queue.mark_failed(correlation_id, error_msg)
        return False, {'error': error_msg}


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
        _photo_queue.mark_in_progress(correlation_id)
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
                                    resp = requests.post(telegram_url, json={
                                        'chat_id': chat_id,
                                        'text': f"📡 Pochtoy:\n{pochtoy_msg}"
                                    }, timeout=5)
                                    
                                    # Сохраняем message_id чтобы можно было удалить
                                    if resp.status_code == 200:
                                        resp_data = resp.json()
                                        if resp_data.get('ok') and resp_data.get('result'):
                                            msg_id = resp_data['result'].get('message_id')
                                            if msg_id:
                                                # Добавляем в SENT_BATCHES если есть
                                                try:
                                                    from shoesbot.telegram_bot import SENT_BATCHES
                                                    if correlation_id in SENT_BATCHES:
                                                        SENT_BATCHES[correlation_id]['message_ids'].append(msg_id)
                                                        logger.info(f"Added Pochtoy message {msg_id} to batch {correlation_id}")
                                                except Exception:
                                                    pass
                                    
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

