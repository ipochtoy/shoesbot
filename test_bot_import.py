#!/usr/bin/env python3
"""
Тесты для проверки бота и окружения
"""
import sys
import os

def test_bot_imports():
    """Проверяет что бот импортируется без ошибок"""
    try:
        import bot
        print("✅ Bot imports OK")
        return True
    except Exception as e:
        print(f"❌ Bot imports FAILED: {e}")
        return False

def test_env_variables():
    """Проверяет что все необходимые переменные окружения установлены"""
    from dotenv import load_dotenv
    load_dotenv()

    required = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY', 'POCHTOY_API_URL']
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"❌ Missing env vars: {missing}")
        return False

    print("✅ Environment variables OK")
    return True

def test_django_connection():
    """Проверяет что Django доступен и БД работает"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shoessite.settings')
    import django
    django.setup()

    try:
        from photos.models import Photo
        count = Photo.objects.count()
        print(f"✅ Django connection OK ({count} photos in DB)")
        return True
    except Exception as e:
        print(f"❌ Django connection FAILED: {e}")
        return False

if __name__ == '__main__':
    os.chdir('/home/pochtoy/shoesbot')

    results = [
        test_bot_imports(),
        test_env_variables(),
        test_django_connection()
    ]

    if all(results):
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
