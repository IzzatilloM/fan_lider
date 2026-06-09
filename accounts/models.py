import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Tizim foydalanuvchisi. Kirish email + parol (Gmail kodi bilan tasdiqlangan)."""

    ROLE_CHOICES = (
        ('admin', _('Administrator')),
        ('director', _('Direktor')),
        ('teacher', _("O'qituvchi")),
        ('student', _("O'quvchi")),
    )

    role = models.CharField(
        _("Rol"), max_length=20, choices=ROLE_CHOICES, default='student'
    )
    phone = models.CharField(_("Telefon"), max_length=20, blank=True)
    avatar = models.ImageField(
        _("Rasm"), upload_to='avatars/', blank=True, null=True
    )
    google_picture = models.URLField(_("Google rasmi"), blank=True)
    # Admin/direktor Telegram bot orqali ro'yxatdan o'tadi: kod aynan shu
    # chat_id ga yuboriladi. Parolni tiklash ham shu orqali.
    telegram_chat_id = models.CharField(
        _("Telegram chat ID"), max_length=32, blank=True, default='', db_index=True,
        help_text=_("Telegram bot bergan ID — tasdiqlash kodi shu yerga yuboriladi."),
    )
    is_verified = models.BooleanField(_("Tasdiqlangan"), default=False)
    # Admin tomonidan yaratilgan o'qituvchi/o'quvchi parolini admin ko'ra olishi uchun
    # (faqat admin yoki tizim tomonidan o'rnatilganda to'ldiriladi).
    plain_password = models.CharField(
        _("Ko'rinadigan parol"), max_length=128, blank=True, default='',
        help_text=_("Admin yaratgan parol — faqat admin panelida ko'rinadi."),
    )
    # Tizimga birinchi marta kirgach parolni majburiy yangilash (admin reset qilgach).
    must_change_password = models.BooleanField(_("Parol yangilanishi shart"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def display_name(self):
        return self.get_full_name() or self.username or self.email

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        if self.google_picture:
            return self.google_picture
        return ''

    @property
    def initials(self):
        full = (self.get_full_name() or self.username or self.email or '?').strip()
        parts = full.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return full[:2].upper()

    @property
    def is_staff_role(self):
        return self.role in ('admin', 'director', 'teacher')

    @property
    def is_director(self):
        return self.role == 'director'

    @property
    def is_admin_role(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def role_home_url(self):
        """Rolga qarab kirgandan keyingi asosiy sahifa nomi."""
        if self.is_superuser or self.role == 'admin':
            return 'dashboard:home'
        if self.role == 'director':
            return 'dashboard:director'
        if self.role == 'teacher':
            return 'dashboard:teacher'
        return 'cabinet:overview'


class TelegramVerificationCode(models.Model):
    """6 xonali tasdiqlash kodi (Telegram bot yoki Gmail orqali yuboriladi).

    Admin/direktor ro'yxatdan o'tishi (signup) va parolni tiklashi (reset)
    uchun ishlatiladi. Kanalga qarab kod foydalanuvchining Telegram `chat_id`
    siga yoki `email` manziliga yuboriladi.
    """

    PURPOSE_CHOICES = (
        ('signup', _("Ro'yxatdan o'tish")),
        ('reset', _("Parolni tiklash")),
    )
    CHANNEL_CHOICES = (
        ('telegram', _('Telegram bot')),
        ('email', _('Gmail')),
    )

    channel = models.CharField(
        _("Kanal"), max_length=10, choices=CHANNEL_CHOICES, default='telegram'
    )
    chat_id = models.CharField(
        _("Telegram chat ID"), max_length=64, blank=True, default='', db_index=True
    )
    email = models.EmailField(_("Email"), blank=True, default='', db_index=True)
    code = models.CharField(_("Kod"), max_length=6)
    purpose = models.CharField(
        _("Maqsad"), max_length=20, choices=PURPOSE_CHOICES, default='signup'
    )
    # Ro'yxatdan o'tishda kiritilgan ma'lumotlarni tasdiqlanguncha saqlaymiz
    payload = models.JSONField(_("Ma'lumotlar"), default=dict, blank=True)

    attempts = models.PositiveSmallIntegerField(_("Urinishlar"), default=0)
    is_used = models.BooleanField(_("Ishlatilgan"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(_("Amal qilish muddati"))

    class Meta:
        verbose_name = _("Tasdiqlash kodi")
        verbose_name_plural = _("Tasdiqlash kodlari")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chat_id} — {self.code} ({self.get_purpose_display()})"

    @staticmethod
    def generate_code():
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def issue(cls, identifier, purpose='signup', payload=None, channel='telegram'):
        """Yangi kod yaratadi va eski (ishlatilmagan) kodlarni bekor qiladi.

        `identifier` — kanalga qarab Telegram chat ID yoki email manzili.
        """
        identifier = str(identifier).strip()
        old = cls.objects.filter(purpose=purpose, channel=channel, is_used=False)
        ttl = getattr(settings, 'TG_CODE_TTL_MINUTES', 10)
        fields = {
            'channel': channel,
            'code': cls.generate_code(),
            'purpose': purpose,
            'payload': payload or {},
            'expires_at': timezone.now() + timedelta(minutes=ttl),
        }
        if channel == 'email':
            old.filter(email__iexact=identifier).update(is_used=True)
            fields['email'] = identifier
        else:
            old.filter(chat_id=identifier).update(is_used=True)
            fields['chat_id'] = identifier
        return cls.objects.create(**fields)

    @classmethod
    def latest_for(cls, identifier, purpose, channel='telegram'):
        """Berilgan kanal/identifikator uchun eng so'nggi ishlatilmagan kod."""
        identifier = str(identifier).strip()
        qs = cls.objects.filter(purpose=purpose, channel=channel, is_used=False)
        if channel == 'email':
            qs = qs.filter(email__iexact=identifier)
        else:
            qs = qs.filter(chat_id=identifier)
        return qs.order_by('-created_at').first()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        max_attempts = getattr(settings, 'TG_CODE_MAX_ATTEMPTS', 5)
        return (
            not self.is_used
            and not self.is_expired
            and self.attempts < max_attempts
        )


class PasswordResetRequest(models.Model):
    """O'qituvchi/o'quvchi Telegram bot orqali yuborgan parol tiklash murojaati.

    Bot foydalanuvchidan rol va loginini so'raydi, murojaat shu yerga tushadi.
    Admin yangi parol o'rnatadi — bot foydalanuvchiga yangi parolni yuboradi.
    """

    ROLE_CHOICES = (
        ('teacher', _("O'qituvchi")),
        ('student', _("O'quvchi")),
    )
    STATUS_CHOICES = (
        ('pending', _('Kutilmoqda')),
        ('resolved', _('Yangi parol berildi')),
        ('rejected', _('Rad etildi')),
    )

    role = models.CharField(_("Rol"), max_length=20, choices=ROLE_CHOICES)
    identifier = models.CharField(
        _("Login / telefon"), max_length=150,
        help_text=_("Foydalanuvchi botda kiritgan login yoki telefon."),
    )
    full_name = models.CharField(_("Ism (botdan)"), max_length=200, blank=True)
    telegram_chat_id = models.CharField(_("Telegram chat ID"), max_length=32, db_index=True)

    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='pending')
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='password_reset_requests', verbose_name=_("Topilgan foydalanuvchi"),
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_reset_requests', verbose_name=_("Hal qilgan admin"),
    )
    note = models.CharField(_("Izoh"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Parol tiklash murojaati")
        verbose_name_plural = _("Parol tiklash murojaatlari")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_role_display()} — {self.identifier} ({self.get_status_display()})"

    def find_user(self):
        """Kiritilgan login/telefon bo'yicha mos foydalanuvchini topishga urinadi."""
        from django.db.models import Q
        from students.models import Student

        ident = (self.identifier or '').strip()
        if not ident:
            return None
        # 1) Username/email bo'yicha
        user = CustomUser.objects.filter(
            Q(username__iexact=ident) | Q(email__iexact=ident), role=self.role
        ).first()
        if user:
            return user
        # 2) O'quvchi bo'lsa telefon bo'yicha
        if self.role == 'student':
            digits = ''.join(ch for ch in ident if ch.isdigit())
            if digits:
                st = Student.objects.filter(
                    Q(phone__contains=digits) | Q(parent_phone__contains=digits)
                ).exclude(user__isnull=True).first()
                if st and st.user_id:
                    return st.user
        return None
