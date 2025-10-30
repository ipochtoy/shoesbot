import os
import re
import asyncio
from io import BytesIO

from dotenv import load_dotenv
from PIL import Image

# Optional imports
try:
    from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode  # type: ignore
    _HAS_ZBAR = True
except Exception:
    _HAS_ZBAR = False

try:
    import cv2  # type: ignore
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

SUPPORTED_SYMBOLS = []
if _HAS_ZBAR:
    from pyzbar.pyzbar import ZBarSymbol  # type: ignore
    SUPPORTED_SYMBOLS = [
        ZBarSymbol.QRCODE,
        ZBarSymbol.EAN13, ZBarSymbol.EAN8,
        ZBarSymbol.UPCA, ZBarSymbol.UPCE,
        ZBarSymbol.CODE39, ZBarSymbol.CODE93, ZBarSymbol.CODE128,
        ZBarSymbol.ITF,
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Пришли фото, извлеку штрихкоды/QR. /ping — проверка.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong")

# Vision OCR helpers

def _vision_text_detect_bytes(content: bytes) -> str:
    from google.cloud import vision  # lazy import
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)
    resp = client.text_detection(image=image)
    if resp.error.message:
        raise RuntimeError(resp.error.message)
    return (resp.full_text_annotation.text or "").strip()

async def decode_with_vision(image_bytes: bytes):
    text = await asyncio.to_thread(_vision_text_detect_bytes, image_bytes)
    digits = re.findall(r"\b(\d{8}|\d{12}|\d{13})\b", text)
    out = []
    seen = set()
    for d in digits:
        if d not in seen:
            seen.add(d)
            out.append(("OCR", d))
    return out

# ZBar decode

def decode_with_zbar(image: Image.Image):
    if not _HAS_ZBAR:
        return []
    results = zbar_decode(image, symbols=SUPPORTED_SYMBOLS)
    out = []
    for r in results:
        try:
            data = r.data.decode("utf-8", errors="replace")
        except Exception:
            data = str(r.data)
        out.append((str(r.type), data))
    return out

# OpenCV QR fallback

def decode_with_cv_qr(image: Image.Image):
    if not _HAS_CV2:
        return []
    import numpy as np  # type: ignore
    arr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    qr = cv2.QRCodeDetector()
    data, points, _ = qr.detectAndDecode(arr)
    if data:
        return [("QRCODE", data)]
    return []

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    largest = update.message.photo[-1]
    file = await context.bot.get_file(largest.file_id)
    buf = BytesIO()
    await file.download_to_memory(out=buf)
    buf.seek(0)

    img = Image.open(buf).convert("RGB")

    results = []
    results.extend(decode_with_zbar(img))
    if not results:
        results.extend(decode_with_cv_qr(img))
    if not results and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            results.extend(await decode_with_vision(buf.getvalue()))
        except Exception as e:
            await update.message.reply_text(f"Vision error: {e}")

    if not results:
        await update.message.reply_text("Коды не нашёл. Сделай фото ближе/резче, без бликов.")
        return

    lines = [f"{i}. {t}: {v}" for i, (t, v) in enumerate(results, 1)]
    await update.message.reply_text("\n".join(lines))

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment (.env)")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
