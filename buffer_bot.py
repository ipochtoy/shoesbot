"""Буферный Telegram бот - просто сохраняет фото в Django без обработки."""
import os
import sys
import asyncio
from io import BytesIO
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import aiohttp
import base64

load_dotenv()

BUFFER_BOT_TOKEN = os.getenv("BUFFER_BOT_TOKEN") or os.getenv("BOT_TOKEN")
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/photos/api/buffer-upload/")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Буферный бот. Отправляй фото - я сохраню их для сортировки.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получил фото → отправил в Django буфер."""
    try:
        if not update.message or not update.message.photo:
            return
        
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        largest = update.message.photo[-1]
        file_id = largest.file_id
        
        # Скачиваем фото
        tg_file = await context.bot.get_file(file_id)
        buf = BytesIO()
        await tg_file.download_to_memory(out=buf)
        image_data = buf.getvalue()
        
        # Конвертим в base64
        img_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Отправляем в Django
        payload = {
            'file_id': file_id,
            'message_id': message_id,
            'chat_id': chat_id,
            'image': img_b64,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DJANGO_API_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    print(f"✅ Photo {file_id[:20]} saved to buffer")
                    # Реакция подтверждения
                    await update.message.react("👍")
                else:
                    print(f"❌ Django error: {resp.status}")
                    await update.message.react("❌")
                    
    except Exception as e:
        print(f"Error in handle_photo: {e}")
        import traceback
        traceback.print_exc()


def main():
    if not BUFFER_BOT_TOKEN:
        print("❌ BUFFER_BOT_TOKEN not set")
        return
    
    print("Starting Buffer Bot...")
    app = Application.builder().token(BUFFER_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Buffer Bot started. Listening for photos...")
    app.run_polling()


if __name__ == "__main__":
    main()

