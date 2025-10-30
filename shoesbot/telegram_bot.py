import os
import uuid
from io import BytesIO
from time import perf_counter
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from shoesbot.pipeline import DecoderPipeline
from shoesbot.decoders.zbar_decoder import ZBarDecoder
from shoesbot.decoders.cv_qr_decoder import OpenCvQrDecoder
from shoesbot.decoders.vision_decoder import VisionDecoder
from shoesbot.renderers.card_renderer import CardRenderer
from shoesbot.logging_setup import logger
from shoesbot.diagnostics import system_info

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

pipeline = DecoderPipeline([ZBarDecoder(), OpenCvQrDecoder(), VisionDecoder()])
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    chat_id = update.effective_chat.id
    is_debug = DEBUG_DEFAULT or (chat_id in DEBUG_CHATS)
    corr = uuid.uuid4().hex[:8]

    largest = update.message.photo[-1]
    t0 = perf_counter()
    tg_file = await context.bot.get_file(largest.file_id)

    buf = BytesIO()
    await tg_file.download_to_memory(out=buf)
    download_ms = int((perf_counter() - t0) * 1000)

    raw = buf.getvalue()
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    if is_debug:
        os.makedirs("data/samples", exist_ok=True)
        with open(f"data/samples/{corr}.jpg", "wb") as f:
            f.write(raw)
        logger.info(f"[{corr}] photo size={len(raw)} bytes")

    if is_debug:
        results, timeline = pipeline.run_debug(img, raw)
    else:
        results = pipeline.run(img, raw)
        timeline = []

    if not results:
        base = "❌ Баркоды не найдены на отправленных фото."
        extra = ""
        if timeline:
            lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" + (f" (err={t['error']})" if t['error'] else "") for t in timeline]
            extra = "\n" + "\n".join(lines)
        await update.message.reply_text(base + extra)
        return

    html = renderer.render_barcodes_html(results)
    if timeline:
        lines = [f"{t['decoder']}: {t['count']} за {t['ms']}ms" for t in timeline]
        html += "\n\n<code>" + " | ".join(lines) + "</code>"
    await update.message.reply_html(html)


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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app
