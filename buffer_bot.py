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
    await update.message.reply_text("Буферный бот. Отправляй фото - я сохраню их для сортировки.\n\n/reprocess - переобработать все фото в буфере (распознать GG заново)")


async def reprocess_buffer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переобработать все фото в буфере - распознать GG лейблы."""
    await update.message.reply_text("🔄 Запускаю переобработку всех фото в буфере...")
    
    try:
        # Отправляем запрос в Django для переобработки
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://127.0.0.1:8000/photos/api/detect-gg-in-buffer/',
                json={},
                timeout=aiohttp.ClientTimeout(total=300)  # 5 минут макс
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    found = data.get('found_count', 0)
                    await update.message.reply_text(f"✅ Готово! Распознано GG лейблов: {found}\n\nТеперь открой /photos/sorting/ и жми 'Автогруппировка'")
                else:
                    await update.message.reply_text(f"❌ Ошибка: {resp.status}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


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
        
        # Быстрое распознавание GG лейбла (без полной обработки)
        gg_label = ''
        try:
            # Простой поиск GG на фото через OpenAI
            import os
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                import requests
                resp = requests.post('https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {openai_key}'},
                    json={
                        'model': 'gpt-4o-mini',
                        'messages': [{
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': 'Find GG label on this image (like GG681, GG700, Q747). Return ONLY the code, nothing else. If no GG label - return "none".'},
                                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                            ]
                        }],
                        'max_tokens': 20
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    text = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip().upper()
                    if text and text != 'NONE' and 'GG' in text or 'Q' in text:
                        gg_label = text
                        print(f"  Found GG: {gg_label}")
        except:
            pass
        
        # Отправляем в Django
        payload = {
            'file_id': file_id,
            'message_id': message_id,
            'chat_id': chat_id,
            'image': img_b64,
            'gg_label': gg_label,
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
    app.add_handler(CommandHandler("reprocess", reprocess_buffer))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Buffer Bot started. Listening for photos...")
    app.run_polling()


if __name__ == "__main__":
    main()

