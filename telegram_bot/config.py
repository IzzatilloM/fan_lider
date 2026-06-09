"""Bot konfiguratsiyasi + Django ORM ulanishi.

Bot Django loyihasining bir qismi sifatida ishlaydi va o'sha bazadan
(kurslar, arizalar, o'quvchilar) foydalanadi.
"""
import os
import sys
from pathlib import Path

import django

# Loyiha ildizini sys.path ga qo'shamiz (telegram_bot/ ning ota-papkasi)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings  # noqa: E402

BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
BRAND_NAME = getattr(settings, 'BRAND_NAME', 'Fan Lider')
CENTER_PHONE = getattr(settings, 'CENTER_PHONE', '+998 90 000 00 00')
CENTER_ADDRESS = getattr(settings, 'CENTER_ADDRESS', "Toshkent sh.")
SITE_URL = getattr(settings, 'SITE_URL', '').rstrip('/')
