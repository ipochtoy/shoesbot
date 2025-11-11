"""
Background worker to retry failed photo uploads.

Runs every 5 minutes and retries pending uploads.
"""
import asyncio
import os
import aiohttp
from datetime import datetime
from shoesbot.logging_setup import logger
from shoesbot.photo_queue import PhotoUploadQueue


DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/photos/api/upload-batch/")


async def retry_pending_uploads():
    """Retry all pending uploads from queue."""
    queue = PhotoUploadQueue()
    
    pending = queue.get_pending_uploads()
    
    if not pending:
        return
    
    logger.info(f"🔄 Retry worker: found {len(pending)} pending uploads")
    
    for upload in pending:
        correlation_id = upload['correlation_id']
        retry_count = upload['retry_count']
        
        logger.info(f"🔄 Retrying upload {correlation_id} (attempt {retry_count + 1})")
        
        try:
            payload = {
                'correlation_id': correlation_id,
                'chat_id': upload['chat_id'],
                'message_ids': upload['message_ids'],
                'photos': upload['photos_data'],
                'barcodes': upload['barcodes_data'],
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    DJANGO_API_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        queue.mark_uploaded(correlation_id)
                        logger.info(f"✅ Retry SUCCESS: {correlation_id}")
                    else:
                        text = await resp.text()
                        error_msg = f"HTTP {resp.status}: {text[:200]}"
                        queue.mark_failed(correlation_id, error_msg)
                        logger.warning(f"❌ Retry failed: {correlation_id} - {error_msg}")
        
        except Exception as e:
            error_msg = str(e)
            queue.mark_failed(correlation_id, error_msg)
            logger.error(f"❌ Retry error: {correlation_id} - {error_msg}")
    
    # Cleanup old uploads
    queue.cleanup_old_uploads(days=7)


async def retry_worker_loop():
    """Main loop - runs every 5 minutes."""
    logger.info("🚀 Photo retry worker started")
    
    while True:
        try:
            await retry_pending_uploads()
        except Exception as e:
            logger.error(f"Retry worker error: {e}", exc_info=True)
        
        # Wait 5 minutes before next check
        await asyncio.sleep(300)


def start_retry_worker():
    """Start retry worker (call from bot.py)."""
    logger.info("Starting photo retry worker...")
    asyncio.create_task(retry_worker_loop())

