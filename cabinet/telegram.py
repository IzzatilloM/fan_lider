"""Telegram orqali o'quvchiga xabar yuborish.

Bot tokeni (settings.TELEGRAM_BOT_TOKEN) va o'quvchining telegram chat_id
(Student.telegram_chat_id) bo'lsa — haqiqiy xabar yuboriladi.
Aks holda funksiya xavfsiz tarzda False qaytaradi (xato chiqarmaydi).

To'liq bot (webhook, kurslar, ariza) 4-fazada qo'shiladi.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(chat_id, text, parse_mode='HTML'):
    """Bitta xabarni yuboradi. Muvaffaqiyatli bo'lsa True."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or not chat_id:
        return False
    try:
        import requests
        resp = requests.post(
            API.format(token=token),
            json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode,
                  'disable_web_page_preview': True},
            timeout=10,
        )
        ok = resp.ok and resp.json().get('ok')
        if not ok:
            logger.warning("Telegram sendMessage muvaffaqiyatsiz: %s", resp.text[:300])
        return bool(ok)
    except Exception:
        logger.exception("Telegram xabar yuborishda xatolik")
        return False


def notify_student_credentials(student, username, password, cabinet_url=''):
    """Admin login yaratganda o'quvchiga kabinet havolasi va parolni yuboradi.

    `cabinet_url` — to'liq (absolyut) havola berilsa, o'sha ishlatiladi
    (view'da `request.build_absolute_uri('/cabinet/')` orqali olinadi).
    Aks holda settings.SITE_URL ga tayanadi.
    """
    chat_id = getattr(student, 'telegram_chat_id', '') or ''
    if not chat_id:
        return False
    if cabinet_url:
        link = cabinet_url.rstrip('/') + '/'
    else:
        base = getattr(settings, 'SITE_URL', '').rstrip('/')
        link = f"{base}/cabinet/" if base else "/cabinet/"
    brand = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    text = (
        f"✅ <b>Tabriklaymiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.</b>\n\n"
        f"🎓 <b>{brand} CRM — shaxsiy kabinet</b>\n\n"
        f"Assalomu alaykum, {student.first_name}!\n"
        f"Administrator arizangizni tasdiqladi va siz uchun shaxsiy kabinet ochildi. "
        f"Bu yerda kurslaringiz, baholaringiz, davomat va to'lovlaringizni kuzatasiz.\n\n"
        f"🔗 Havola: {link}\n"
        f"👤 Login: <code>{username}</code>\n"
        f"🔑 Parol: <code>{password}</code>\n\n"
        f"Parolni hech kimga bermang."
    )
    return send_message(chat_id, text)


def notify_new_password(chat_id, username, password, role_label="Foydalanuvchi"):
    """Admin parolni tiklagach foydalanuvchiga yangi parolni yuboradi."""
    if not chat_id:
        return False
    brand = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    text = (
        f"🔑 <b>{brand} CRM — yangi parol</b>\n\n"
        f"Administrator parolingizni yangiladi.\n\n"
        f"👤 Login: <code>{username}</code>\n"
        f"🔑 Yangi parol: <code>{password}</code>\n\n"
        f"Tizimga kirib, parolni o'zgartirib qo'yishingiz mumkin. "
        f"Parolni hech kimga bermang."
    )
    return send_message(chat_id, text)
