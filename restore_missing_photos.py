#!/usr/bin/env python3
"""
Скрипт для восстановления пропавших фоток из Telegram.

Если файлы были удалены, но записи в базе остались,
можно попробовать скачать их заново из Telegram по file_id.
"""

import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shoessite'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoessite.settings')
django.setup()

from photos.models import Photo
import requests
from django.core.files.base import ContentFile
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env")
    sys.exit(1)

def get_file_from_telegram(file_id):
    """Получить файл из Telegram по file_id."""
    # Получаем информацию о файле
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
    response = requests.get(url, params={'file_id': file_id})
    if not response.ok:
        return None
    
    file_info = response.json()
    if not file_info.get('ok'):
        return None
    
    file_path = file_info['result']['file_path']
    
    # Скачиваем файл
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    file_response = requests.get(download_url)
    if not file_response.ok:
        return None
    
    return file_response.content

def restore_photo(photo):
    """Восстановить одно фото."""
    if not photo.file_id:
        print(f"  Photo {photo.id}: нет file_id")
        return False
    
    try:
        file_content = get_file_from_telegram(photo.file_id)
        if not file_content:
            print(f"  Photo {photo.id}: не удалось скачать из Telegram")
            return False
        
        # Сохраняем файл
        photo.image.save(
            os.path.basename(photo.image.path),
            ContentFile(file_content),
            save=True
        )
        print(f"  ✅ Photo {photo.id}: восстановлено")
        return True
    except Exception as e:
        print(f"  ❌ Photo {photo.id}: ошибка - {e}")
        return False

def main():
    """Основная функция."""
    print("🔍 Ищу пропавшие фотки...")
    
    missing = []
    for photo in Photo.objects.filter(image__isnull=False):
        if not os.path.exists(photo.image.path):
            missing.append(photo)
    
    print(f"📊 Найдено {len(missing)} пропавших фоток")
    
    if not missing:
        print("✅ Все фотки на месте!")
        return
    
    print("\n🔄 Начинаю восстановление...")
    print("⚠️  ВНИМАНИЕ: Это может занять много времени!")
    print("⚠️  Telegram API имеет лимиты на запросы\n")
    
    restored = 0
    failed = 0
    
    for i, photo in enumerate(missing[:100], 1):  # Ограничиваем 100 для теста
        print(f"[{i}/{min(100, len(missing))}] Photo {photo.id} (batch {photo.batch.correlation_id})...")
        if restore_photo(photo):
            restored += 1
        else:
            failed += 1
    
    print(f"\n✅ Восстановлено: {restored}")
    print(f"❌ Не удалось: {failed}")
    print(f"📊 Всего пропавших: {len(missing)}")

if __name__ == '__main__':
    main()

