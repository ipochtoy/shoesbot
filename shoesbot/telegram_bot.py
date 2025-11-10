import os
import sys

# Fix for pyzbar on macOS - must be before any imports
if sys.platform == "darwin":
    zbar_lib = "/opt/homebrew/lib"
    if os.path.exists(zbar_lib):
        current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
        if zbar_lib not in current_dyld:
            os.environ["DYLD_LIBRARY_PATH"] = f"{zbar_lib}:{current_dyld}".rstrip(":")

import uuid
import asyncio
from io import BytesIO
from dotenv import load_dotenv
from time import perf_counter
from PIL import Image
from telegram import Update, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from typing import Optional
from telegram.request import HTTPXRequest

from shoesbot.pipeline import DecoderPipeline
from shoesbot.decoders.zbar_decoder import ZBarDecoder
from shoesbot.decoders.cv_qr_decoder import OpenCvQrDecoder
from shoesbot.decoders.vision_decoder import VisionDecoder
from shoesbot.decoders.gg_label_decoder import GGLabelDecoder
from shoesbot.renderers.card_renderer import CardRenderer
from shoesbot.logging_setup import logger
from shoesbot.diagnostics import system_info
from shoesbot.metrics import append_event, summarize
from shoesbot.admin import get_admin_id, set_admin_id
from shoesbot.photo_buffer import buffer as photo_buffer
from shoesbot.django_upload import upload_batch_to_django
from shoesbot.cache_manager import get_cache
from shoesbot.barcode_database import get_barcode_db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

pipeline = DecoderPipeline([ZBarDecoder(), OpenCvQrDecoder(), VisionDecoder(), GGLabelDecoder()])
renderer = CardRenderer(templates_dir=os.path.join(os.path.dirname(__file__), "..", "templates"))

DEBUG_DEFAULT = os.getenv("DEBUG", "0") in ("1", "true", "True")
DEBUG_CHATS: set[int] = set()
USE_PARALLEL_DECODERS = os.getenv("PARALLEL_DECODERS", "1") == "1"

# Storage for photos waiting for GG label
PENDING_WITHOUT_GG: dict = {}  # {chat_id: {'photos': [...], 'message_ids': [...]}}
USE_SMART_SKIP = os.getenv("SMART_SKIP_VISION", "0") == "1"  # Disabled by default

# In-memory registry of sent messages per batch (correlation id)
# SENT_BATCHES[corr] = { 'chat_id': int, 'message_ids': [int] }
SENT_BATCHES: dict[str, dict] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message - bot works without this command."""
    welcome_text = (
        "👋 <b>ShoesBot готов к работе!</b>\n\n"
        "📸 Просто пришли фото товара - я автоматически:\n"
        "  • Найду все штрих-коды и QR-коды\n"
        "  • Распознаю GG лейблы и Q-коды\n"
        "  • Создам карточку товара\n\n"
        "📊 <b>Команды:</b>\n"
        "/analytics - полная статистика работы\n"
        "/top_barcodes - топ отсканированных кодов\n"
        "/cache_stats - статистика кэша Vision API\n"
        "/ping - проверка связи\n\n"
        "Бот работает <b>всегда</b>, команда /start не обязательна! 🚀"
    )
    await update.message.reply_html(welcome_text)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong")

async def debug_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    DEBUG_CHATS.add(update.effective_chat.id)
    await update.message.reply_text("debug: ON")

async def debug_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    DEBUG_CHATS.discard(update.effective_chat.id)
    await update.message.reply_text("debug: OFF")

async def diag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(system_info())

async def admin_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = update.effective_chat.id
    set_admin_id(cid)
    await update.message.reply_text(f"admin set: {cid}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = summarize(500)
    text = f"total={s['total']}, ok={s['ok']}, empty={s['empty']}, per_decoder={s['per_decoder_hits']}"
    await update.message.reply_text(text)

async def cache_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Vision API cache statistics."""
    cache = get_cache()
    stats = cache.get_stats()
    text = (
        f"💾 Vision API Cache Stats:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"✅ Cache hits: {stats['hits']}\n"
        f"❌ Cache misses: {stats['misses']}\n"
        f"📊 Hit rate: {stats['hit_rate_percent']}%\n"
        f"📁 Cached files: {stats['cached_files']}\n"
        f"🔢 Total requests: {stats['total_requests']}"
    )
    await update.message.reply_text(text)

async def barcode_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show barcode database statistics."""
    db = get_barcode_db()
    stats = db.get_stats()

    text = "📊 Barcode Database Stats:\n━━━━━━━━━━━━━━━━\n"
    text += f"🏷️ Unique barcodes: {stats.get('total_unique_barcodes', 0)}\n"
    text += f"📷 Total scans: {stats.get('total_scans', 0)}\n"
    text += f"📅 Scanned today: {stats.get('scanned_today', 0)}\n"

    most_scanned = stats.get('most_scanned')
    if most_scanned:
        name = most_scanned.get('product_name') or 'Unknown'
        count = most_scanned.get('scan_count', 0)
        code = most_scanned.get('barcode', '')
        text += f"\n🏆 Most scanned:\n{code}\n({name}, {count} times)"

    await update.message.reply_text(text)

async def top_barcodes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top 10 most scanned barcodes."""
    db = get_barcode_db()
    top = db.get_top_barcodes(limit=10)

    if not top:
        await update.message.reply_text("📊 No barcodes scanned yet")
        return

    text = "🏆 Top 10 Most Scanned:\n━━━━━━━━━━━━━━━━\n\n"
    for idx, item in enumerate(top, 1):
        code = item['barcode']
        count = item['scan_count']
        name = item['product_name'] or 'Unknown'
        text += f"{idx}. {code}\n   {name} ({count}x)\n\n"

    await update.message.reply_text(text)

async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comprehensive analytics dashboard in Telegram."""
    try:
        # Gather all statistics
        from shoesbot.metrics import get_all_events
        from datetime import datetime, timedelta

        events = get_all_events()
        db = get_barcode_db()
        cache = get_cache()

        # Overall stats
        total_scans = len(events)
        success_scans = sum(1 for e in events if e.get('result_count', 0) > 0)
        empty_scans = total_scans - success_scans
        success_rate = round(success_scans / total_scans * 100, 1) if total_scans > 0 else 0

        # Average processing time
        total_times = []
        for event in events:
            timeline = event.get('timeline', [])
            total_time = sum(t.get('ms', 0) for t in timeline)
            total_times.append(total_time)
        avg_time = round(sum(total_times) / len(total_times), 1) if total_times else 0

        # Database stats
        db_stats = db.get_stats()
        cache_stats = cache.get_stats()

        # Recent activity (last 24h)
        now = datetime.now()
        cutoff_24h = now - timedelta(hours=24)
        recent_scans = 0
        for event in events:
            try:
                ts = datetime.fromisoformat(event['ts'])
                if ts >= cutoff_24h:
                    recent_scans += 1
            except:
                pass

        # Decoder performance
        decoder_stats = {}
        for event in events:
            for decoder_info in event.get('timeline', []):
                decoder_name = decoder_info.get('decoder', 'unknown')
                if decoder_name not in decoder_stats:
                    decoder_stats[decoder_name] = {'hits': 0, 'total': 0, 'time': 0}
                decoder_stats[decoder_name]['total'] += 1
                if decoder_info.get('count', 0) > 0:
                    decoder_stats[decoder_name]['hits'] += 1
                decoder_stats[decoder_name]['time'] += decoder_info.get('ms', 0)

        # Format message
        text = "📊 <b>ANALYTICS DASHBOARD</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        text += "📈 <b>Общая статистика:</b>\n"
        text += f"  • Всего сканирований: <b>{total_scans}</b>\n"
        text += f"  • Успешных: <b>{success_scans}</b> ({success_rate}%)\n"
        text += f"  • Пустых: {empty_scans}\n"
        text += f"  • За последние 24ч: <b>{recent_scans}</b>\n"
        text += f"  • Среднее время: <b>{avg_time}ms</b>\n\n"

        text += "🏷️ <b>База данных кодов:</b>\n"
        text += f"  • Уникальных кодов: <b>{db_stats.get('total_unique_barcodes', 0)}</b>\n"
        text += f"  • Всего сканирований: <b>{db_stats.get('total_scans', 0)}</b>\n"
        text += f"  • Отсканировано сегодня: <b>{db_stats.get('scanned_today', 0)}</b>\n\n"

        most_scanned = db_stats.get('most_scanned')
        if most_scanned:
            code = most_scanned.get('barcode', 'N/A')
            count = most_scanned.get('scan_count', 0)
            name = most_scanned.get('product_name') or 'Unknown'
            text += f"🏆 <b>Самый популярный код:</b>\n"
            text += f"  <code>{code}</code>\n"
            text += f"  {name} ({count}x)\n\n"

        text += "💾 <b>Cache Vision API:</b>\n"
        text += f"  • Hit rate: <b>{cache_stats.get('hit_rate_percent', 0)}%</b>\n"
        text += f"  • Hits: {cache_stats.get('hits', 0)}\n"
        text += f"  • Misses: {cache_stats.get('misses', 0)}\n"
        text += f"  • Cached files: {cache_stats.get('cached_files', 0)}\n\n"

        text += "⚙️ <b>Производительность декодеров:</b>\n"
        for decoder_name, stats in decoder_stats.items():
            avg_decoder_time = round(stats['time'] / stats['total'], 1) if stats['total'] > 0 else 0
            hit_rate = round(stats['hits'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
            text += f"  • <b>{decoder_name}</b>: {avg_decoder_time}ms, {hit_rate}% hits\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "🔄 Автообновление: отправьте команду снова"

        await update.message.reply_html(text)

    except Exception as e:
        logger.error(f"Error in analytics command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка получения статистики: {str(e)}")

async def safe_send_message(bot, chat_id: int, text: str, parse_mode: str = None, max_retries: int = 3) -> bool:
    """Send message with retry logic. Returns True if successful, False otherwise."""
    for attempt in range(max_retries):
        try:
            if parse_mode:
                await bot.send_message(chat_id, text, parse_mode=parse_mode)
            else:
                await bot.send_message(chat_id, text)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                logger.warning(f"safe_send_message: attempt {attempt+1}/{max_retries} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"safe_send_message: failed after {max_retries} attempts: {e}")
                return False
    return False

async def safe_send_media_group(bot, chat_id: int, media_group: list, max_retries: int = 3) -> bool:
    """Send media group with retry logic. Returns True if successful, False otherwise."""
    for attempt in range(max_retries):
        try:
            await bot.send_media_group(chat_id, media_group)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                logger.warning(f"safe_send_media_group: attempt {attempt+1}/{max_retries} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"safe_send_media_group: failed after {max_retries} attempts: {e}")
                return False
    return False

async def send_message_ret(bot, chat_id: int, text: str, parse_mode: Optional[str] = None, reply_markup=None, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                logger.warning(f"send_message_ret: retry {attempt+1}/{max_retries} in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"send_message_ret: failed after retries: {e}")
                return None

async def send_media_group_ret(bot, chat_id: int, media_group: list, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await bot.send_media_group(chat_id, media_group)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                logger.warning(f"send_media_group_ret: retry {attempt+1}/{max_retries} in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"send_media_group_ret: failed after retries: {e}")
                return []

async def process_photo_batch(chat_id: int, photo_items: list, context: ContextTypes.DEFAULT_TYPE, status_msg=None) -> None:
    """Process a batch of photos."""
    try:
        logger.info(f"process_photo_batch: starting, chat={chat_id}, items={len(photo_items)}")
        is_debug = DEBUG_DEFAULT or (chat_id in DEBUG_CHATS)
        corr = uuid.uuid4().hex[:8]

        # Show typing indicator
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Failed to send typing action: {e}")

        all_results = []
        all_timelines = []
        barcode_to_photo_map = []  # List of (barcode, photo_index) tuples

        # Обновляем прогресс: начало обработки
        if status_msg:
            try:
                await status_msg.edit_text(f"🔍 Обработка {len(photo_items)} фото...")
            except Exception as e:
                logger.debug(f"Failed to update progress: {e}")

        # Параллельная обработка всех фото одновременно
        async def process_single_photo(idx: int, item) -> tuple:
            """Обработать одно фото и вернуть результаты."""
            logger.info(f"process_photo_batch: processing item {idx+1}/{len(photo_items)}")

            t0 = perf_counter()
            buf = BytesIO()
            await item.file_obj.download_to_memory(out=buf)
            download_ms = int((perf_counter() - t0) * 1000)

            raw = buf.getvalue()
            buf.seek(0)
            img = Image.open(buf).convert("RGB")

            # Use smart parallel or regular parallel decoders
            if USE_PARALLEL_DECODERS:
                if USE_SMART_SKIP:
                    results, timeline = await pipeline.run_smart_parallel_debug(img, raw)
                else:
                    results, timeline = await pipeline.run_parallel_debug(img, raw)
            else:
                results, timeline = pipeline.run_debug(img, raw)

            append_event({
                'corr': corr,
                'chat_id': chat_id,
                'result_count': len(results),
                'download_ms': download_ms,
                'timeline': timeline,
                'size_bytes': len(raw),
            })

            return results, timeline, idx

        # Запускаем обработку всех фото параллельно
        tasks = [process_single_photo(idx, item) for idx, item in enumerate(photo_items)]
        photo_results = await asyncio.gather(*tasks)

        # Собираем результаты в правильном порядке
        photo_results.sort(key=lambda x: x[2])  # Сортируем по индексу
        for results, timeline, photo_idx in photo_results:
            all_results.extend(results)
            all_timelines.extend(timeline)
            # Track which photo each barcode came from
            for barcode in results:
                barcode_to_photo_map.append((barcode, photo_idx))

        # Record all barcodes in database
        db = get_barcode_db()
        new_barcodes = []
        repeat_barcodes = []
        for barcode in all_results:
            info = db.record_scan(barcode.data, barcode.symbology, chat_id, barcode.source)
            if info.get('is_new'):
                new_barcodes.append(barcode.data)
            else:
                repeat_barcodes.append((barcode.data, info.get('scan_count', 0)))

        # Don't send diagnostic messages to chat (only log them)
        
        # Delete original messages
        logger.info(f"process_photo_batch: deleting {len(photo_items)} original messages")
        for item in photo_items:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=item.message_id)
            except Exception as e:
                logger.warning(f"process_photo_batch: failed to delete message {item.message_id}: {e}")
        
        # Split results: GG from OCR decoder AND Q-codes from ZBar (CODE39/Q codes are our GG labels)
        gg_from_ocr = [r for r in all_results if r.source == "gg-label"]
        gg_from_q = [r for r in all_results if r.symbology == "CODE39" and r.data.startswith("Q")]
        gg_results = gg_from_ocr + gg_from_q
        
        # Regular barcodes (excluding Q codes which are GG)
        regular_barcodes = [r for r in all_results if r.source != "gg-label" and not (r.symbology == "CODE39" and r.data.startswith("Q"))]
        
        # All barcodes for card (regular + GG labels)
        barcode_results = regular_barcodes + gg_results
        
        logger.info(f"GG labels: {len(gg_results)} ({len(gg_from_ocr)} from OCR, {len(gg_from_q)} from Q-codes)")
        logger.info(f"Regular barcodes: {len(regular_barcodes)}")
        logger.info(f"Total for card: {len(barcode_results)}")
        
        # Send: PLACE4174 + photo album + card (with GG labels) + PLACE4174
        # Each message has retry logic, but we continue sequentially
        
        # Prepare registry for this batch
        SENT_BATCHES[corr] = { 'chat_id': chat_id, 'message_ids': [] }
        reg = SENT_BATCHES[corr]['message_ids']

        # First PLACE4174
        logger.info("process_photo_batch: sending PLACE4174")
        m0 = await send_message_ret(context.bot, chat_id, "PLACE4174")
        if m0:
            reg.append(m0.message_id)
        await asyncio.sleep(0.2)  # Баланс между скоростью и стабильностью
        
        # Send photo album
        logger.info(f"process_photo_batch: sending media group with {len(photo_items)} photos")

        # Show upload_photo indicator
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        except Exception as e:
            logger.debug(f"Failed to send upload_photo action: {e}")

        media_group = [InputMediaPhoto(item.file_id) for item in photo_items]
        mg = await send_media_group_ret(context.bot, chat_id, media_group)
        if mg:
            reg.extend([m.message_id for m in mg])
        await asyncio.sleep(0.2)  # Баланс между скоростью и стабильностью
        
        # Проверяем наличие GG лейблов (GG текст + Q баркод)
        gg_text_codes = [r for r in barcode_results if r.symbology == 'GG_LABEL' and r.data.startswith('GG')]
        q_barcode_codes = [r for r in barcode_results if r.symbology == 'GG_LABEL' and r.data.startswith('Q')]
        
        has_gg_pair = len(gg_text_codes) > 0 and len(q_barcode_codes) > 0
        gg_labels = [r for r in barcode_results if r.symbology == 'GG_LABEL']
        
        # Если не нашли ИЛИ нет полной пары GG+Q - пробуем OpenAI на ВСЕХ фото
        if not gg_labels or not has_gg_pair:
            logger.info("Trying OpenAI on all photos for GG/Q detection...")
            try:
                import base64
                import requests as sync_requests
                import re
                from shoesbot.models import Barcode
                
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key:
                    # Пробуем каждое фото
                    for idx, photo_item in enumerate(photo_items):
                        try:
                            buf2 = BytesIO()
                            await photo_item.file_obj.download_to_memory(out=buf2)
                            img_data = buf2.getvalue()
                            img_b64 = base64.b64encode(img_data).decode('utf-8')
                            
                            resp = sync_requests.post('https://api.openai.com/v1/chat/completions',
                                headers={'Authorization': f'Bearer {openai_key}'},
                                json={
                                    'model': 'gpt-4o-mini',
                                    'messages': [{
                                        'role': 'user',
                                        'content': [
                                            {
                                                'type': 'text',
                                                'text': '''Find ALL codes on this product:

1. GG code - LARGE BLACK TEXT on yellow sticker (like GG727, GG681)
2. Q code - numbers UNDER or NEAR the barcode lines (like Q2622988, Q747)

IMPORTANT:
- Q code is usually 7-10 digits starting with Q
- Look UNDER the barcode stripes
- Q code can be small text
- Check EVERY corner and label

Return ALL codes found, one per line:
GG727
Q2622988

If you find only GG, still return it.
If no codes at all, return "NONE"'''
                                            },
                                            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                                        ]
                                    }],
                                    'max_tokens': 50,
                                    'temperature': 0
                                },
                                timeout=15
                            )
                            
                            if resp.status_code == 200:
                                text = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip().upper()
                                logger.info(f"OpenAI photo {idx+1} response: {text}")
                                
                                # Ищем GG и Q коды
                                gg_matches = re.findall(r'\b(GG\d{2,7})\b', text)
                                q_matches = re.findall(r'\b(Q\d{4,10})\b', text)
                                
                                for match in gg_matches + q_matches:
                                    # Проверяем что еще не добавили
                                    if not any(r.data == match for r in gg_labels):
                                        gg_labels.append(Barcode(
                                            symbology='GG_LABEL',
                                            data=match,
                                            source='openai-emergency'
                                        ))
                                        barcode_results.append(gg_labels[-1])
                                        logger.info(f"OpenAI emergency found: {match}")
                        except Exception as photo_err:
                            logger.error(f"OpenAI photo {idx+1} error: {photo_err}")
                            continue
            except Exception as e:
                logger.error(f"OpenAI emergency GG detection failed: {e}")
        
        # Перепроверяем наличие полной пары после OpenAI
        gg_text_codes = [r for r in barcode_results if r.symbology == 'GG_LABEL' and r.data.startswith('GG')]
        q_barcode_codes = [r for r in barcode_results if r.symbology == 'GG_LABEL' and r.data.startswith('Q')]
        has_gg_pair = len(gg_text_codes) > 0 and len(q_barcode_codes) > 0
        gg_labels = [r for r in barcode_results if r.symbology == 'GG_LABEL']
        
        if not gg_labels:
            # GG лейбла не найдена - сохраняем фото и просим догрузить
            logger.warning(f"process_photo_batch: NO GG LABEL FOUND for {corr}")
            
            # Сохраняем эти фото как "ожидающие GG"
            PENDING_WITHOUT_GG[chat_id] = {
                'photos': photo_items,
                'message_ids': reg.copy()
            }
            logger.info(f"Saved {len(photo_items)} photos to PENDING_WITHOUT_GG for chat {chat_id}")
            
            error_msg = "❌ <b>GG лейбла не найдена!</b>\n\n"
            error_msg += "Не могу создать карточку без GG кода.\n\n"
            error_msg += "📸 <b>Отправь фото лейбы (желтый стикер с GG кодом)</b>\n\n"
            error_msg += "Код обычно выглядит как:\n"
            error_msg += "  • GG681\n"
            error_msg += "  • GG700\n"
            error_msg += "  • Q2622911\n\n"
            error_msg += f"У меня уже есть <b>{len(photo_items)} фото</b> товара. "
            error_msg += "После получения фото лейбы я объединю все и создам полную карточку."
            
            m_error = await send_message_ret(context.bot, chat_id, error_msg, parse_mode='HTML')
            if m_error:
                reg.append(m_error.message_id)
            
            # НЕ создаем карточку и НЕ загружаем в Django
            logger.info("process_photo_batch: STOPPED - waiting for GG label photo")
            return
        
        # GG найдена - проверяем есть ли ожидающие фото
        logger.info(f"process_photo_batch: GG labels found: {[g.data for g in gg_labels]}")
        
        # Объединяем с ожидающими фото если есть
        all_photos = list(photo_items)
        old_message_ids = []
        
        if chat_id in PENDING_WITHOUT_GG:
            pending = PENDING_WITHOUT_GG.pop(chat_id)
            old_photos = pending['photos']
            old_message_ids = pending['message_ids']
            
            logger.info(f"Found pending photos: {len(old_photos)}. Merging with current {len(photo_items)}")
            
            # Добавляем старые фото в начало
            all_photos = list(old_photos) + all_photos
            
            # Объединяем message_ids для удаления старых сообщений
            reg.extend(old_message_ids)
            
            # Перезапускаем распознавание на всех фото (старые + новые)
            logger.info("Re-running barcode detection on all photos...")
            all_barcode_results = []
            tasks = []
            for idx, item in enumerate(all_photos):
                tasks.append(process_single_photo(idx, item))
            
            photo_results = await asyncio.gather(*tasks)
            for pr in photo_results:
                all_barcode_results.extend(pr['results'])
            
            # Используем объединенные результаты
            barcode_results = all_barcode_results
            photo_items = all_photos
        
        # Card (includes both regular barcodes and GG labels)
        logger.info(f"process_photo_batch: rendering card with {len(photo_items)} total photos")
        
        # Добавляем статус распознавания
        if has_gg_pair:
            html = "✅ <b>GG лейбла найдена (полная пара)</b>\n"
            html += f"🏷️ GG: {', '.join([r.data for r in gg_text_codes])}\n"
            html += f"🔢 Q: {', '.join([r.data for r in q_barcode_codes])}\n\n"
        else:
            html = "⚠️ <b>Неполная пара GG/Q</b>\n"
            if gg_text_codes:
                html += f"🏷️ GG: {', '.join([r.data for r in gg_text_codes])}\n"
            if q_barcode_codes:
                html += f"🔢 Q: {', '.join([r.data for r in q_barcode_codes])}\n"
            html += "\n"
        
        if len(old_message_ids) > 0:
            html += f"📦 Объединено фото: {len(photo_items)}\n\n"

        # Add barcode history info
        if new_barcodes:
            html += f"🆕 Новые коды: {len(new_barcodes)}\n"
        if repeat_barcodes:
            html += f"🔁 Повторные коды: {len(repeat_barcodes)}\n"
            # Show most frequent repeats
            top_repeats = sorted(repeat_barcodes, key=lambda x: x[1], reverse=True)[:3]
            if top_repeats:
                repeat_info = ", ".join([f"{code[:10]}... ({count}x)" for code, count in top_repeats])
                html += f"   {repeat_info}\n"
        if new_barcodes or repeat_barcodes:
            html += "\n"

        html += renderer.render_barcodes_html(barcode_results, photo_count=len(photo_items))
        if is_debug and all_timelines:
            lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" for t in all_timelines]
            html += "\n\n<code>" + " | ".join(lines) + "</code>"
        m_card = await send_message_ret(context.bot, chat_id, html, parse_mode='HTML')
        if m_card:
            reg.append(m_card.message_id)
        await asyncio.sleep(0.2)  # Баланс между скоростью и стабильностью
        
        # Final PLACE4174 - can be closed manually if needed
        logger.info("process_photo_batch: sending final PLACE4174")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Удалить всё", callback_data=f"del:{corr}")]])
        m_end = await send_message_ret(context.bot, chat_id, "PLACE4174", reply_markup=kb)
        if m_end:
            reg.append(m_end.message_id)
        
        # Upload to Django in background
        message_ids_list = [item.message_id for item in photo_items]
        try:
            upload_success = await upload_batch_to_django(corr, chat_id, message_ids_list, photo_items, all_results, barcode_to_photo_map)
            if not upload_success:
                # Django upload failed
                await context.bot.send_message(chat_id, "❌❌❌\n\nОшибка загрузки в Django")
        except Exception as e:
            logger.error(f"process_photo_batch: django upload error: {e}")
            await context.bot.send_message(chat_id, "❌❌❌\n\nОшибка загрузки в Django")
        
        logger.info("process_photo_batch: done")
    except Exception as e:
        logger.error(f"process_photo_batch: error: {e}", exc_info=True)
        # Notify user about critical error
        try:
            await context.bot.send_message(chat_id, f"❌❌❌\n\nКритическая ошибка обработки:\n{str(e)[:200]}")
        except:
            pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.info("handle_photo: received photo")
        if not update.message or not update.message.photo:
            logger.warning("handle_photo: no message or photo")
            return
        
        chat_id = update.effective_chat.id
        largest = update.message.photo[-1]
        file_id = largest.file_id
        message_id = update.message.message_id
        logger.info(f"handle_photo: chat={chat_id}, file_id={file_id[:20]}..., message_id={message_id}")
        tg_file = await context.bot.get_file(file_id)
        logger.info(f"handle_photo: got tg_file")
        
        # Add to buffer
        is_first, photo_batch = photo_buffer.add(chat_id, file_id, tg_file, message_id)
        logger.info(f"handle_photo: added to buffer, is_first={is_first}, batch_size={len(photo_batch) if photo_batch else 0}")
        
        if is_first:
            # First photo AND no timer running: show "Началась обработка..." and schedule delayed processing
            status_msg = None
            try:
                status_msg = await context.bot.send_message(chat_id, "🔍 Началась обработка...")
                logger.info("handle_photo: sent status message, scheduling delayed_process")
            except Exception as e:
                logger.error(f"handle_photo: failed to send status message: {e}")
                # Продолжаем без статуса
            
            async def delayed_process():
                # Ждем полный timeout буфера (3.0s) + небольшой запас для сбора до 10 фото
                wait_time = 3.2
                logger.info(f"delayed_process: sleeping {wait_time}s for chat={chat_id}")
                await asyncio.sleep(wait_time)
                logger.info(f"delayed_process: flushing buffer for chat={chat_id}")
                
                # Debug: check buffer state
                import shoesbot.photo_buffer as pb_mod
                logger.info(f"delayed_process: buffer state: {list(pb_mod.buffer.buffers.keys())}")
                if chat_id in pb_mod.buffer.buffers:
                    logger.info(f"delayed_process: buffer[{chat_id}] size: {len(pb_mod.buffer.buffers[chat_id])}")
                
                flushed = photo_buffer.flush(chat_id)
                logger.info(f"delayed_process: flushed={flushed is not None}, size={len(flushed) if flushed else 0}")
                if flushed:
                    logger.info("delayed_process: calling process_photo_batch")
                    await process_photo_batch(chat_id, flushed, context, status_msg)
                    # Delete status message after processing completes
                    if status_msg:
                        try:
                            await status_msg.delete()
                            logger.info("delayed_process: deleted status message")
                        except Exception as e:
                            logger.error(f"delayed_process: failed to delete status: {e}")
                    logger.info("delayed_process: done")
                else:
                    pass
            
            # Schedule background task
            context.application.create_task(delayed_process())
            logger.info("handle_photo: task scheduled")
        elif is_first:
            pass
    except Exception as e:
        logger.error(f"handle_photo: error: {e}", exc_info=True)


def build_app() -> Application:
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment (.env)")
    # Оптимизированные таймауты и пул соединений для быстрой работы
    request = HTTPXRequest(
        connection_pool_size=20,  # Увеличил размер пула соединений
        connect_timeout=10.0, 
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=30.0,  # Увеличил таймаут пула
        media_write_timeout=30.0  # Для загрузки фото
    )
    app = Application.builder().token(token).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("analytics", analytics))
    app.add_handler(CommandHandler("debug_on", debug_on))
    app.add_handler(CommandHandler("debug_off", debug_off))
    app.add_handler(CommandHandler("diag", diag))
    app.add_handler(CommandHandler("admin_on", admin_on))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("cache_stats", cache_stats))
    app.add_handler(CommandHandler("barcode_stats", barcode_stats))
    app.add_handler(CommandHandler("top_barcodes", top_barcodes))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(on_delete_batch, pattern=r"^del:"))
    return app


async def on_delete_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        data = query.data or ""
        corr = data.split(":", 1)[1] if ":" in data else data
        entry = SENT_BATCHES.pop(corr, None)
        if not entry:
            # Nothing to delete
            try:
                await query.edit_message_text("PLACE4174 (ничего не найдено для удаления)")
            except Exception:
                pass
            return
        chat_id = entry['chat_id']
        ids = entry['message_ids']
        
        # Удаляем карточку из Django
        try:
            django_url = os.getenv('DJANGO_URL', 'http://127.0.0.1:8000')
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f'{django_url}/photos/api/delete-card-by-correlation/{corr}/',
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"Django card deleted: {result}")
                        deleted_info = f"Карточка удалена ({result.get('photos_deleted', 0)} фото)"
                    else:
                        logger.warning(f"Django delete failed: {resp.status}")
                        deleted_info = "❌❌❌ Ошибка удаления карточки из Django"
        except Exception as django_err:
            logger.error(f"Django delete error: {django_err}")
            deleted_info = "❌❌❌ Django недоступен"
        
        # Delete in reverse order (from last to first)
        for mid in sorted(set(ids), reverse=True):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception as e:
                logger.debug(f"on_delete_batch: failed to delete {mid}: {e}")
        
        # Confirm
        try:
            await context.bot.send_message(chat_id, f"🗑️ Удалено:\n- Сообщения в Telegram\n- {deleted_info}")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"on_delete_batch: error: {e}")
