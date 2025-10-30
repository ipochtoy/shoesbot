import os
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from shoesbot.pipeline import DecoderPipeline
from shoesbot.decoders.zbar_decoder import ZBarDecoder
from shoesbot.decoders.cv_qr_decoder import OpenCvQrDecoder
from shoesbot.decoders.vision_decoder import VisionDecoder
from shoesbot.renderers.card_renderer import CardRenderer

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

pipeline = DecoderPipeline([ZBarDecoder(), OpenCvQrDecoder(), VisionDecoder()])
renderer = CardRenderer(templates_dir=os.path.join(os.path.dirname(__file__), "..", "templates"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html("Пришли фото, извлеку штрихкоды/QR. /ping — проверка.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    largest = update.message.photo[-1]
    tg_file = await context.bot.get_file(largest.file_id)
    buf = BytesIO()
    await tg_file.download_to_memory(out=buf)
    raw = buf.getvalue()
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    results = pipeline.run(img, raw)
    if not results:
        await update.message.reply_text("Коды не нашёл. Сделай фото ближе/резче, без бликов.")
        return

    html = renderer.render_barcodes_html(results)
    await update.message.reply_html(html)


def build_app() -> Application:
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment (.env)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app
