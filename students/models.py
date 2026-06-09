from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Student(models.Model):
    """O'quvchi profili."""

    GENDER_CHOICES = (
        ('male', _("O'g'il bola")),
        ('female', _("Qiz bola")),
    )
    STATUS_CHOICES = (
        ('active', _("Faol")),
        ('frozen', _("Muzlatilgan")),
        ('graduated', _("Bitirgan")),
        ('left', _("Tark etgan")),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='student_profile',
    )
    first_name = models.CharField(_("Ism"), max_length=100)
    last_name = models.CharField(_("Familiya"), max_length=100)
    middle_name = models.CharField(_("Otasining ismi"), max_length=100, blank=True)

    phone = models.CharField(_("Telefon"), max_length=20)
    parent_phone = models.CharField(_("Ota-ona telefoni"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    gender = models.CharField(_("Jinsi"), max_length=10, choices=GENDER_CHOICES, default='male')
    birth_date = models.DateField(_("Tug'ilgan sana"), null=True, blank=True)
    address = models.CharField(_("Manzil"), max_length=255, blank=True)
    school_name = models.CharField(_("Maktab"), max_length=150, blank=True)
    grade = models.CharField(_("Sinf"), max_length=20, blank=True)

    photo = models.ImageField(_("Rasm"), upload_to='students/', blank=True, null=True)
    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='active')
    balance = models.DecimalField(
        _("Balans (so'm)"), max_digits=12, decimal_places=2, default=0,
        help_text=_("Manfiy = qarzdor"),
    )
    note = models.TextField(_("Izoh"), blank=True)
    telegram_chat_id = models.CharField(
        _("Telegram chat ID"), max_length=32, blank=True, db_index=True,
        help_text=_("O'quvchi bot orqali ro'yxatdan o'tganda to'ldiriladi (bot xabar yuborish uchun)."),
    )
    slug = models.SlugField(unique=True, blank=True, max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("O'quvchi")
        verbose_name_plural = _("O'quvchilar")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.first_name}-{self.last_name}") or 'student'
            slug = base
            i = 1
            while Student.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse('students:detail', kwargs={'slug': self.slug})

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}".strip()

    @property
    def short_name(self):
        return f"{self.first_name} {self.last_name[:1] + '.' if self.last_name else ''}".strip()

    @property
    def initials(self):
        a = self.first_name[:1] if self.first_name else ''
        b = self.last_name[:1] if self.last_name else ''
        return (a + b).upper() or '?'

    @property
    def is_debtor(self):
        return self.balance < 0

    @property
    def debt_amount(self):
        return abs(self.balance) if self.balance < 0 else Decimal('0')

    @property
    def active_enrollments(self):
        return self.enrollments.filter(status='active').select_related('course')

    @property
    def attendance_percentage(self):
        records = self.attendances.all()
        total = records.count()
        if not total:
            return 0
        present = records.filter(status__in=['present', 'late']).count()
        return round(present / total * 100)

    @property
    def average_score(self):
        agg = self.assessments.aggregate(models.Avg('percentage'))
        return round(agg['percentage__avg'] or 0, 1)
