"""
Development settings for eBay development environment.

This file extends the base settings.py but uses a separate dev database
to avoid affecting production (warehouse, bot).
"""
from .settings import *

# Dev-specific settings
DEBUG = True
ALLOWED_HOSTS = ['*']

# Separate dev database (copy of production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'dev_db.sqlite3',
    }
}

# Dev server settings
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Use /dev/ prefix in URLs (when nginx rewrite doesn't work)
ROOT_URLCONF = 'shoessite.urls_dev'

print("🔧 DEV MODE: Using dev_db.sqlite3 and urls_dev.py")

