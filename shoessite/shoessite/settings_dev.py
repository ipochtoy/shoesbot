"""
Development settings - ПОЛНАЯ ИЗОЛЯЦИЯ от production.

Использует отдельную БД, media, static в директории dev_data/
Это защищает production от случайных изменений при разработке.
"""
from .settings import *

# Dev-specific settings
DEBUG = True
ALLOWED_HOSTS = ['*']

# Отдельная БД для dev (полная изоляция от production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'dev_data' / 'db.sqlite3',
    }
}

# Отдельные media и static для dev
MEDIA_ROOT = BASE_DIR.parent / 'dev_data' / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = BASE_DIR.parent / 'dev_data' / 'static'
STATIC_URL = '/static/'

# Отключаем внешние API в dev режиме
POCHTOY_API_ENABLED = False

# Dev server settings
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Use /dev/ prefix in URLs (when nginx rewrite doesn't work)
ROOT_URLCONF = 'shoessite.urls_dev'

print("🔧 DEV MODE: Using isolated dev_data/ directory")

