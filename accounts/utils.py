"""Hisob (accounts) uchun yordamchi funksiyalar.

Admin/direktor o'zini ro'yxatdan o'tkazadi va parolni tiklaydi: tasdiqlash
kodi tanlangan kanal orqali — Telegram bot (chat ID) yoki Gmail (email) —
yuboriladi.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def director_exists():
    """Tizimda allaqachon direktor bormi?"""
    from .models import CustomUser
    return CustomUser.objects.filter(role='director').exists()


def admin_slots_left():
    """Yana nechta admin ro'yxatdan o'ta oladi."""
    from .models import CustomUser
    limit = getattr(settings, 'MAX_ADMINS', 2)
    return max(limit - CustomUser.objects.filter(role='admin').count(), 0)


def director_slots_left():
    """Yana nechta direktor ro'yxatdan o'ta oladi (odatda 0 yoki 1)."""
    from .models import CustomUser
    limit = getattr(settings, 'MAX_DIRECTORS', 1)
    return max(limit - CustomUser.objects.filter(role='director').count(), 0)


def available_register_roles():
    """Ro'yxatdan o'tish formasida ko'rsatiladigan rollar (key, label).

    Administrator va Direktor doim ko'rinadi — limit to'lgan bo'lsa, tanlangach
    `RegisterForm.clean_role` aniq xabar bilan ogohlantiradi (forma "buzilgan"
    ko'rinmasligi uchun rol kartalari har doim chiqadi)."""
    return [
        ('admin', 'Administrator'),
        ('director', 'Direktor'),
    ]


def apply_role_for_new_user(user, requested_role=None):
    """Yangi (o'zi ro'yxatdan o'tgan) foydalanuvchiga rol beradi.

    Faqat 'admin' va 'director' o'zini ro'yxatdan o'tkaza oladi.
    - requested_role='director' va bo'sh joy bo'lsa -> direktor.
    - requested_role='admin' va bo'sh joy bo'lsa -> administrator (superuser).
    - Tizim butunlay bo'sh bo'lsa birinchi foydalanuvchi avto-admin bo'ladi.
    """
    if requested_role == 'director' and director_slots_left() > 0:
        user.role = 'director'
        user.is_staff = True
        user.is_superuser = False
        return

    if requested_role == 'admin' and admin_slots_left() > 0:
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        return

    # Zaxira: birinchi foydalanuvchi avto-admin bo'ladi (tizim bo'sh bo'lsa)
    if admin_slots_left() > 0:
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
    else:
        user.role = 'student'
        user.is_staff = False
        user.is_superuser = False


def allowed_admin_ids():
    """Tizimga kira oladigan administratorlar id'lari (eng ko'p MAX_ADMINS ta).

    Tartib: eng erta yaratilganlar (created_at) ustun.
    """
    from .models import CustomUser

    limit = getattr(settings, 'MAX_ADMINS', 2)
    admins = list(
        CustomUser.objects.filter(role='admin').order_by('created_at', 'id')
        .values_list('id', flat=True)
    )
    return admins[:limit]


def admin_login_allowed(user):
    """Admin foydalanuvchi limitdan tashqarida bo'lsa False qaytaradi.

    Superuser har doim kira oladi (zaxira kirish — bot ishlamay qolsa ham).
    """
    if user.role != 'admin':
        return True
    if user.is_superuser:
        return True
    return user.id in allowed_admin_ids()


def _code_action(verification):
    return "parolingizni tiklash" if verification.purpose == 'reset' else "ro'yxatdan o'tishni yakunlash"


def send_verification(verification):
    """Kodni `verification.channel` ga qarab Telegram yoki Gmail orqali yuboradi."""
    if verification.channel == 'email':
        return send_code_email(verification)
    return send_code_telegram(verification)


def send_code_telegram(verification):
    """Tasdiqlash kodini Telegram bot orqali foydalanuvchining chat_id siga yuboradi.

    Muvaffaqiyatli bo'lsa True. Bot tokeni yo'q yoki foydalanuvchi botni
    ishga tushirmagan bo'lsa (chat topilmasa) False qaytaradi.
    """
    from cabinet.telegram import send_message

    brand = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    ttl = getattr(settings, 'TG_CODE_TTL_MINUTES', 10)
    text = (
        f"🔐 <b>{brand} CRM — tasdiqlash kodi</b>\n\n"
        f"Tizimda {_code_action(verification)} uchun kodingiz:\n\n"
        f"<code>{verification.code}</code>\n\n"
        f"Kod {ttl} daqiqa amal qiladi. Agar bu siz bo'lmasangiz, "
        f"ushbu xabarni e'tiborsiz qoldiring."
    )
    return send_message(verification.chat_id, text)


def send_code_email(verification):
    """Tasdiqlash kodini Gmail (email) orqali yuboradi. Muvaffaqiyatli bo'lsa True.

    SMTP sozlanmagan bo'lsa (EMAIL_BACKEND=console) kod konsolga chiqadi —
    bu ham True hisoblanadi, shunda oqim to'xtab qolmaydi.
    """
    from django.core.mail import EmailMultiAlternatives

    email = (verification.email or '').strip()
    if not email:
        return False

    brand = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    ttl = getattr(settings, 'TG_CODE_TTL_MINUTES', 10)
    action = _code_action(verification)
    subject = f"{brand} CRM — tasdiqlash kodi: {verification.code}"
    text = (
        f"{brand} CRM\n\n"
        f"Tizimda {action} uchun tasdiqlash kodingiz: {verification.code}\n\n"
        f"Kod {ttl} daqiqa amal qiladi. Agar bu siz bo'lmasangiz, "
        f"ushbu xabarni e'tiborsiz qoldiring."
    )
    brand_color = getattr(settings, 'BRAND_COLOR', '#D4640F')
    html = f"""
    <div style="margin:0;padding:24px;background:#0e1420;font-family:'Segoe UI',Arial,sans-serif;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center">
          <table role="presentation" width="440" cellpadding="0" cellspacing="0"
                 style="max-width:440px;background:#ffffff;border-radius:18px;overflow:hidden;
                        box-shadow:0 20px 50px rgba(0,0,0,.35);">
            <tr><td style="background:linear-gradient(135deg,{brand_color},#9c4509);padding:26px 28px;">
              <div style="color:#fff;font-size:18px;font-weight:800;">{brand} CRM</div>
              <div style="color:rgba(255,255,255,.85);font-size:13px;margin-top:2px;">O'quv markazi boshqaruv tizimi</div>
            </td></tr>
            <tr><td style="padding:28px;">
              <p style="margin:0 0 6px;color:#161b26;font-size:15px;font-weight:700;">Tasdiqlash kodi</p>
              <p style="margin:0 0 18px;color:#7a8294;font-size:13px;line-height:1.5;">
                Tizimda {action} uchun quyidagi kodni kiriting:</p>
              <div style="text-align:center;margin:0 0 18px;">
                <span style="display:inline-block;letter-spacing:.4em;font-size:32px;font-weight:800;
                             color:{brand_color};background:#fdf1ea;border:1px solid #f6e0d2;
                             border-radius:14px;padding:14px 22px;">{verification.code}</span>
              </div>
              <p style="margin:0;color:#7a8294;font-size:12px;line-height:1.5;">
                Kod <b>{ttl} daqiqa</b> amal qiladi. Agar bu siz bo'lmasangiz, ushbu xabarni e'tiborsiz qoldiring.</p>
            </td></tr>
            <tr><td style="padding:14px 28px;background:#f7f8fb;color:#9aa1b1;font-size:11px;">
              © {brand} CRM — barcha huquqlar himoyalangan</td></tr>
          </table>
        </td></tr>
      </table>
    </div>"""

    try:
        msg = EmailMultiAlternatives(
            subject, text, settings.DEFAULT_FROM_EMAIL, [email]
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Tasdiqlash kodini email orqali yuborib bo'lmadi: %s", email)
        return False
