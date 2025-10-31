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
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

pipeline = DecoderPipeline([ZBarDecoder(), OpenCvQrDecoder(), VisionDecoder(), GGLabelDecoder()])
renderer = CardRenderer(templates_dir=os.path.join(os.path.dirname(__file__), "..", "templates"))

DEBUG_DEFAULT = os.getenv("DEBUG", "0") in ("1", "true", "True")
DEBUG_CHATS: set[int] = set()
USE_PARALLEL_DECODERS = os.getenv("PARALLEL_DECODERS", "1") == "1"
USE_SMART_SKIP = os.getenv("SMART_SKIP_VISION", "0") == "1"  # Disabled by default

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html("Пришли фото, извлеку штрихкоды/QR. /ping — проверка.")

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

async def process_photo_batch(chat_id: int, photo_items: list, context: ContextTypes.DEFAULT_TYPE, status_msg=None) -> None:
    """Process a batch of photos."""
    try:
        logger.info(f"process_photo_batch: starting, chat={chat_id}, items={len(photo_items)}")
        is_debug = DEBUG_DEFAULT or (chat_id in DEBUG_CHATS)
        corr = uuid.uuid4().hex[:8]
        
        all_results = []
        all_timelines = []
        
        # Process each photo
        for idx, item in enumerate(photo_items):
            logger.info(f"process_photo_batch: processing item {idx+1}/{len(photo_items)}")
            
            # Update progress bar
            if status_msg:
                try:
                    await status_msg.edit_text(f"🔍 Обработка фото {idx+1}/{len(photo_items)}...")
                except Exception as e:
                    logger.debug(f"Failed to update progress: {e}")
            
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
            all_results.extend(results)
            all_timelines.extend(timeline)
            
            append_event({
                'corr': corr,
                'chat_id': chat_id,
                'result_count': len(results),
                'download_ms': download_ms,
                'timeline': timeline,
                'size_bytes': len(raw),
            })
        
        # Notify admin if needed
        admin_id = get_admin_id()
        had_error = any(t.get('error') for t in all_timelines)
        if admin_id and (len(all_results) == 0 or had_error):
            lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" + (f" (err={t['error']})" if t['error'] else "") for t in all_timelines]
            summary = "\n".join(lines)
            try:
                await context.bot.send_message(admin_id, f"[{corr}] chat={chat_id} results={len(all_results)} photos={len(photo_items)}\n" + summary)
            except Exception:
                pass
        
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
        barcode_results = [r for r in all_results if r.source != "gg-label" and not (r.symbology == "CODE39" and r.data.startswith("Q"))]
        
        logger.info(f"GG labels: {len(gg_results)} ({len(gg_from_ocr)} from OCR, {len(gg_from_q)} from Q-codes)")
        logger.info(f"Regular barcodes: {len(barcode_results)}")
        
        # Send: PLACE4174 + photo album + card + GG label + PLACE4174
        logger.info("process_photo_batch: sending PLACE4174")
        await context.bot.send_message(chat_id, "PLACE4174")
        
        # Send photo album
        logger.info(f"process_photo_batch: sending media group with {len(photo_items)} photos")
        media_group = [InputMediaPhoto(item.file_id) for item in photo_items]
        await context.bot.send_media_group(chat_id, media_group)
        
        # Card
        logger.info("process_photo_batch: rendering and sending card")
        html = renderer.render_barcodes_html(barcode_results, photo_count=len(photo_items))
        if is_debug and all_timelines:
            lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" for t in all_timelines]
            html += "\n\n<code>" + " | ".join(lines) + "</code>"
        await context.bot.send_message(chat_id, html, parse_mode='HTML')
        
        # GG label
        if gg_results:
            logger.info(f"process_photo_batch: sending GG labels: {len(gg_results)}")
            gg_lines = ["Наша лейба GG и ее номер:"]
            for gg in gg_results:
                if gg.data.startswith("Q") and gg.data[1:].isdigit():
                    # Q code: show as "Q2623026 (GG765)"
                    q_num = gg.data[1:]
                    gg_lines.append(f"Q{q_num}")
                else:
                    # Direct GG code
                    gg_lines.append(gg.data)
            await context.bot.send_message(chat_id, "\n".join(gg_lines))
        
        # Final PLACE4174
        logger.info("process_photo_batch: sending final PLACE4174")
        await context.bot.send_message(chat_id, "PLACE4174")
        logger.info("process_photo_batch: done")
    except Exception as e:
        logger.error(f"process_photo_batch: error: {e}", exc_info=True)


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
            # First photo: show "Началась обработка..." and schedule delayed processing
            status_msg = await context.bot.send_message(chat_id, "🔍 Началась обработка...")
            logger.info("handle_photo: sent status message, scheduling delayed_process")
            
            async def delayed_process():
                logger.info(f"delayed_process: sleeping 1.5s for chat={chat_id}")
                await asyncio.sleep(1.5)
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
                    try:
                        await status_msg.delete()
                        logger.info("delayed_process: deleted status message")
                    except Exception as e:
                        logger.error(f"delayed_process: failed to delete status: {e}")
                    logger.info("delayed_process: done")
            
            # Schedule background task
            context.application.create_task(delayed_process())
            logger.info("handle_photo: task scheduled")
    except Exception as e:
        logger.error(f"handle_photo: error: {e}", exc_info=True)


def build_app() -> Application:
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment (.env)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("debug_on", debug_on))
    app.add_handler(CommandHandler("debug_off", debug_off))
    app.add_handler(CommandHandler("diag", diag))
    app.add_handler(CommandHandler("admin_on", admin_on))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app
