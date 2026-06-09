from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class RegistrationApplication(models.Model):
    """Onlayn ro'yxatdan o'tish arizasi (potensial o'quvchi).

    Ommaviy sahifadan to'ldiriladi, keyin xodim tomonidan
    qayta ishlanib o'quvchiga aylantiriladi (CRM lead funnel).
    """

    STATUS_CHOICES = (
        ('new', _("Yangi")),
        ('contacted', _("Bog'lanildi")),
        ('trial', _("Sinov darsida")),
        ('enrolled', _("Ro'yxatga olindi")),
        ('rejected', _("Rad etildi")),
    )
    SOURCE_CHOICES = (
        ('website', _("Veb-sayt")),
        ('instagram', _("Instagram")),
        ('telegram', _("Telegram")),
        ('friend', _("Tanish/Do'st")),
        ('banner', _("Reklama banneri")),
        ('other', _("Boshqa")),
    )

    full_name = models.CharField(_("F.I.O"), max_length=200)
    phone = models.CharField(_("Telefon"), max_length=20)
    parent_phone = models.CharField(_("Ota-ona telefoni"), max_length=20, blank=True)
    age = models.PositiveIntegerField(_("Yosh"), null=True, blank=True)

    subject = models.ForeignKey(
        'courses.Subject', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='applications', verbose_name=_("Qiziqqan yo'nalish"),
    )
    preferred_course = models.ForeignKey(
        'courses.Course', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='applications', verbose_name=_("Tanlangan guruh"),
    )

    source = models.CharField(_("Qayerdan"), max_length=20, choices=SOURCE_CHOICES, default='website')
    message = models.TextField(_("Xabar / Izoh"), blank=True)
    telegram_chat_id = models.CharField(
        _("Telegram chat ID"), max_length=32, blank=True, db_index=True,
        help_text=_("Bot orqali kelgan arizada to'ldiriladi (kabinet havolasini yuborish uchun)."),
    )

    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_applications', verbose_name=_("Mas'ul xodim"),
    )
    converted_student = models.OneToOneField(
        'students.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='source_application', verbose_name=_("Yaratilgan o'quvchi"),
    )
    staff_note = models.TextField(_("Xodim izohi"), blank=True)

    created_at = models.DateTimeField(_("Yuborilgan vaqt"), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Onlayn ariza")
        verbose_name_plural = _("Onlayn arizalar")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} — {self.get_status_display()}"

    @property
    def is_open(self):
        return self.status not in ('enrolled', 'rejected')


class Enrollment(models.Model):
    """O'quvchining muayyan guruhga yozilishi."""

    STATUS_CHOICES = (
        ('active', _("Faol")),
        ('frozen', _("Muzlatilgan")),
        ('completed', _("Yakunlangan")),
        ('cancelled', _("Bekor qilingan")),
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='enrollments',
        verbose_name=_("O'quvchi"),
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='enrollments',
        verbose_name=_("Guruh"),
    )
    monthly_fee = models.DecimalField(_("Oylik to'lov"), max_digits=12, decimal_places=2, default=0)
    discount_percent = models.PositiveIntegerField(_("Chegirma (%)"), default=0)

    start_date = models.DateField(_("Boshlangan sana"), default=timezone.now)
    end_date = models.DateField(_("Tugagan sana"), null=True, blank=True)
    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Yozilish")
        verbose_name_plural = _("Yozilishlar")
        ordering = ['-created_at']
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} → {self.course}"

    def save(self, *args, **kwargs):
        if not self.monthly_fee and self.course_id:
            self.monthly_fee = self.course.monthly_fee
        super().save(*args, **kwargs)

    @property
    def net_fee(self):
        """Chegirma hisobga olingan oylik to'lov."""
        if self.discount_percent:
            return self.monthly_fee * (100 - self.discount_percent) / 100
        return self.monthly_fee
