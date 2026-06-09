"""Telegram botni LOKAL sinash uchun — long polling (getUpdates).

PythonAnywhere'da bot webhook orqali ishlaydi, lekin lokal kompyuterda
Telegram webhook yubora olmaydi (localhost'ga yetib bo'lmaydi). Shuning uchun
lokal sinov uchun shu komanda getUpdates bilan xabarlarni o'zi so'rab oladi va
cabinet.bot.handle_update ga uzatadi — webhook bilan bir xil mantiq.

Foydalanish:
  python manage.py run_bot          # botni ishga tushiradi (Ctrl+C bilan to'xtaydi)

Eslatma: ishga tushganda webhook o'chiriladi (getUpdates va webhook birga
ishlamaydi). Deploydan keyin yana webhook o'rnatish uchun:
  python manage.py set_telegram_webhook
"""
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from cabinet import bot


class Command(BaseCommand):
    help = "Telegram botni lokal sinash (long polling)"

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=30,
                            help="Long polling timeout (soniya, default 30)")

    def handle(self, *args, **opts):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN .env da yo'q."))
            return
        base = f"https://api.telegram.org/bot{token}/"

        # Bot kimligini tekshiramiz
        try:
            me = requests.get(base + 'getMe', timeout=10).json()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Telegram'ga ulanib bo'lmadi: {e}"))
            return
        if not me.get('ok'):
            self.stderr.write(self.style.ERROR(f"Token noto'g'ri: {me}"))
            return
        uname = me['result'].get('username')
        self.stdout.write(self.style.SUCCESS(f"✅ Bot ulandi: @{uname}"))

        # getUpdates va webhook birga ishlamaydi — webhookni o'chiramiz
        requests.post(base + 'deleteWebhook',
                      json={'drop_pending_updates': False}, timeout=10)

        # "/" buyruqlar menyusiga /id ni qo'shamiz (lokalda ham ko'rinsin)
        try:
            requests.post(base + 'setMyCommands', json={'commands': [
                {'command': 'start', 'description': "Bosh menyu"},
                {'command': 'id', 'description': "🆔 Telegram ID raqamim"},
                {'command': 'royxat', 'description': "📝 Ro'yxatdan o'tish"},
                {'command': 'kurslar', 'description': "📚 Kurslar va guruhlar"},
                {'command': 'parol', 'description': "🔑 Parolni tiklash"},
                {'command': 'aloqa', 'description': "📞 Aloqa"},
            ]}, timeout=10)
        except Exception:
            pass

        self.stdout.write("📡 Long polling boshlandi. To'xtatish: Ctrl+C")
        self.stdout.write(f"   Telegram'da @{uname} ni oching va /start bosing.\n")

        offset = None
        timeout = opts['timeout']
        while True:
            try:
                params = {'timeout': timeout, 'allowed_updates': ['message', 'callback_query']}
                if offset is not None:
                    params['offset'] = offset
                r = requests.get(base + 'getUpdates', params=params, timeout=timeout + 10).json()
                if not r.get('ok'):
                    self.stderr.write(f"getUpdates xato: {r}")
                    time.sleep(3)
                    continue
                for upd in r.get('result', []):
                    offset = upd['update_id'] + 1
                    try:
                        bot.handle_update(upd)
                    except Exception:
                        import traceback
                        self.stderr.write(self.style.WARNING(
                            f"Update'ni ishlashda xato (update_id={upd['update_id']}):"))
                        self.stderr.write(traceback.format_exc())
            except KeyboardInterrupt:
                self.stdout.write("\n👋 Bot to'xtatildi.")
                break
            except requests.exceptions.ReadTimeout:
                continue
            except Exception as e:
                self.stderr.write(f"Polling xatosi: {e}")
                time.sleep(3)
