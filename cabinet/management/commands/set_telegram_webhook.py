"""Telegram webhook'ni o'rnatish / o'chirish / holatini ko'rish.

Foydalanish:
  python manage.py set_telegram_webhook            # SITE_URL asosida o'rnatadi
  python manage.py set_telegram_webhook --url https://foo.pythonanywhere.com
  python manage.py set_telegram_webhook --delete   # webhookni o'chiradi
  python manage.py set_telegram_webhook --info      # joriy holat
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Telegram bot webhook'ni boshqaradi"

    def add_arguments(self, parser):
        parser.add_argument('--url', help='Sayt manzili (https://...)')
        parser.add_argument('--delete', action='store_true', help="Webhookni o'chirish")
        parser.add_argument('--info', action='store_true', help='Webhook holati')

    def handle(self, *args, **opts):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN .env da yo'q.")
            return
        base = f"https://api.telegram.org/bot{token}/"

        if opts['info']:
            r = requests.get(base + 'getWebhookInfo', timeout=10).json()
            self.stdout.write(str(r))
            return

        if opts['delete']:
            r = requests.post(base + 'deleteWebhook', timeout=10).json()
            self.stdout.write("O'chirildi: " + str(r))
            return

        site = (opts.get('url') or getattr(settings, 'SITE_URL', '')).rstrip('/')
        if not site:
            self.stderr.write("SITE_URL yoki --url kerak (masalan: https://foo.pythonanywhere.com)")
            return
        hook = f"{site}/cabinet/telegram/webhook/"
        payload = {'url': hook, 'allowed_updates': ['message', 'callback_query']}
        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if secret:
            payload['secret_token'] = secret
        r = requests.post(base + 'setWebhook', json=payload, timeout=10).json()
        self.stdout.write(f"Webhook: {hook}\nNatija: {r}")

        # Bot buyruqlar menyusi ("/" tugmasi) — serverdan o'rnatiladi, keshlanmaydi.
        # "/id" har doim ko'rinadi: admin/direktor Telegram ID sini shu orqali oladi.
        commands = [
            {'command': 'start', 'description': "Bosh menyu"},
            {'command': 'id', 'description': "🆔 Telegram ID raqamim (ro'yxatdan o'tish uchun)"},
            {'command': 'royxat', 'description': "📝 Ro'yxatdan o'tish"},
            {'command': 'kurslar', 'description': "📚 Kurslar va guruhlar"},
            {'command': 'parol', 'description': "🔑 Parolni tiklash"},
            {'command': 'aloqa', 'description': "📞 Aloqa"},
        ]
        rc = requests.post(base + 'setMyCommands', json={'commands': commands}, timeout=10).json()
        self.stdout.write(f"Buyruqlar menyusi (/id qo'shildi): {rc.get('ok', rc)}")
