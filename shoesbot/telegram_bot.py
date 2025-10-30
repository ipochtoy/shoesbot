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

async def process_photo_batch(chat_id: int, photo_files: list, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a batch of photos."""
    is_debug = DEBUG_DEFAULT or (chat_id in DEBUG_CHATS)
    corr = uuid.uuid4().hex[:8]
    
    all_results = []
    all_timelines = []
    
    # Process each photo
    for tg_file in photo_files:
        t0 = perf_counter()
        buf = BytesIO()
        await tg_file.download_to_memory(out=buf)
        download_ms = int((perf_counter() - t0) * 1000)
        
        raw = buf.getvalue()
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        
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
            await context.bot.send_message(admin_id, f"[{corr}] chat={chat_id} results={len(all_results)} photos={len(photo_files)}\n" + summary)
        except Exception:
            pass
    
    # Split results
    gg_results = [r for r in all_results if r.source == "gg-label"]
    barcode_results = [r for r in all_results if r.source != "gg-label"]
    
    # Send: PLACE4174 + photo album + card + GG label + PLACE4174
    await context.bot.send_message(chat_id, "PLACE4174")
    
    # Send photo album
    media_group = [InputMediaPhoto(photo.file_id) for photo in photo_files]
    await context.bot.send_media_group(chat_id, media_group)
    
    # Card
    html = renderer.render_barcodes_html(barcode_results, photo_count=len(photo_files))
    if is_debug and all_timelines:
        lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" for t in all_timelines]
        html += "\n\n<code>" + " | ".join(lines) + "</code>"
    await context.bot.send_message(chat_id, html, parse_mode='HTML')
    
    # GG label
    if gg_results:
        gg_lines = ["Наша лейба GG и ее номер:"]
        for gg in gg_results:
            gg_lines.append(gg.data)
        await context.bot.send_message(chat_id, "\n".join(gg_lines))
    
    # Final PLACE4174
    await context.bot.send_message(chat_id, "PLACE4174")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    
    chat_id = update.effective_chat.id
    largest = update.message.photo[-1]
    tg_file = await context.bot.get_file(largest.file_id)
    
    # Add to buffer
    is_first, photo_batch = photo_buffer.add(chat_id, tg_file)
    
    if is_first:
        # First photo, schedule delayed processing
        async def delayed_process():
            await asyncio.sleep(3.0)
            flushed = photo_buffer.flush(chat_id)
            if flushed:
                await process_photo_batch(chat_id, flushed, context)
        
        # Schedule background task
        context.application.create_task(delayed_process())


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
