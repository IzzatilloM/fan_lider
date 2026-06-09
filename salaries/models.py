from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

UZB_MONTHS = [
    _("Yanvar"), _("Fevral"), _("Mart"), _("Aprel"), _("May"), _("Iyun"),
    _("Iyul"), _("Avgust"), _("Sentabr"), _("Oktabr"), _("Noyabr"), _("Dekabr"),
]


def month_name(m):
    return UZB_MONTHS[m - 1] if 1 <= m <= 12 else str(m)


class Employee(models.Model):
    """Markaz xodimi — oylik hisoblash uchun profil.

    Tizim foydalanuvchisiga (CustomUser) bog'lanishi mumkin, lekin shart emas.
    """

    POSITION_CHOICES = (
        ('teacher', _("O'qituvchi")),
        ('manager', _("Menejer / Qabul")),
        ('admin', _("Administrator")),
        ('support', _("Yordamchi xodim")),
        ('cleaner', _("Farrosh")),
        ('guard', _("Qorovul")),
        ('other', _("Boshqa")),
    )

    EMPLOYMENT_CHOICES = (
        ('fixed', _("Belgilangan oylik")),
        ('hourly', _("Soatbay")),
        ('per_student', _("O'quvchi soniga qarab")),
        ('mixed', _("Aralash (oylik + KPI)")),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employee_profile', verbose_name=_("Foydalanuvchi"),
    )
    full_name = models.CharField(_("F.I.O."), max_length=255)
    position = models.CharField(_("Lavozim"), max_length=20, choices=POSITION_CHOICES, default='teacher')
    employment_type = models.CharField(
        _("Ish turi"), max_length=20, choices=EMPLOYMENT_CHOICES, default='mixed'
    )

    base_salary = models.DecimalField(_("Belgilangan oylik (so'm)"), max_digits=12, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(_("Soatlik stavka (so'm)"), max_digits=12, decimal_places=2, default=0)
    per_student_rate = models.DecimalField(_("Har bir o'quvchi uchun (so'm)"), max_digits=12, decimal_places=2, default=0)

    kpi_bonus_pct = models.DecimalField(
        _("KPI bonusi (oylikning %)"), max_digits=5, decimal_places=2, default=Decimal('20'),
        help_text=_("Davomat va o'zlashtirishga qarab beriladigan maksimal bonus foizi."),
    )
    late_penalty = models.DecimalField(
        _("Bitta kechikish jarimasi (so'm)"), max_digits=10, decimal_places=2, default=0
    )

    card_number = models.CharField(_("Plastik karta"), max_length=30, blank=True)
    hire_date = models.DateField(_("Ishga kirgan sana"), null=True, blank=True)
    is_active = models.BooleanField(_("Faol"), default=True)
    note = models.TextField(_("Izoh"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Xodim")
        verbose_name_plural = _("Xodimlar")
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.get_position_display()})"

    @property
    def initials(self):
        parts = (self.full_name or '?').split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.full_name[:2].upper()

    @property
    def instructor(self):
        """Bog'langan o'qituvchi profili (bo'lsa)."""
        if self.user and hasattr(self.user, 'instructor_profile'):
            return self.user.instructor_profile
        return None


class SalaryPeriod(models.Model):
    """Oylik davri (yil + oy)."""

    STATUS_CHOICES = (
        ('draft', _("Qoralama")),
        ('closed', _("Yopilgan")),
    )

    year = models.PositiveIntegerField(_("Yil"))
    month = models.PositiveSmallIntegerField(_("Oy"))
    status = models.CharField(_("Holat"), max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_salary_periods',
    )

    class Meta:
        verbose_name = _("Oylik davri")
        verbose_name_plural = _("Oylik davrlari")
        unique_together = ('year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{month_name(self.month)} {self.year}"

    @property
    def label(self):
        return f"{month_name(self.month)} {self.year}"

    @property
    def total_payout(self):
        return self.records.aggregate(s=models.Sum('total_amount'))['s'] or Decimal('0')


class SalaryRecord(models.Model):
    """Bitta xodimning bitta davr uchun oylik hisob-kitobi."""

    STATUS_CHOICES = (
        ('draft', _("Hisoblandi")),
        ('approved', _("Tasdiqlandi")),
        ('paid', _("To'landi")),
    )

    period = models.ForeignKey(SalaryPeriod, on_delete=models.CASCADE, related_name='records')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_records')

    # --- Kirish metrikalari ---
    worked_days = models.PositiveSmallIntegerField(_("Ishlagan kunlar"), default=0)
    worked_hours = models.DecimalField(_("Ishlagan soatlar"), max_digits=7, decimal_places=1, default=0)
    lessons_count = models.PositiveIntegerField(_("O'tilgan darslar"), default=0)
    groups_count = models.PositiveIntegerField(_("Guruhlar soni"), default=0)
    students_count = models.PositiveIntegerField(_("O'quvchilar soni"), default=0)
    attendance_rate = models.DecimalField(_("Davomat (%)"), max_digits=5, decimal_places=2, default=0)
    avg_score = models.DecimalField(_("O'rtacha o'zlashtirish (%)"), max_digits=5, decimal_places=2, default=0)
    late_count = models.PositiveSmallIntegerField(_("Kechikishlar"), default=0)
    absence_count = models.PositiveSmallIntegerField(_("Sababsiz kelmaslik"), default=0)
    manual_bonus = models.DecimalField(_("Qo'shimcha bonus (so'm)"), max_digits=12, decimal_places=2, default=0)
    manual_penalty = models.DecimalField(_("Qo'shimcha jarima (so'm)"), max_digits=12, decimal_places=2, default=0)
    metrics_note = models.CharField(_("Izoh"), max_length=255, blank=True)

    # --- Hisoblangan tarkib ---
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hours_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    students_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kpi_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalties_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Jami (so'm)"), max_digits=12, decimal_places=2, default=0)
    kpi_score = models.DecimalField(_("KPI ko'rsatkichi (0-100)"), max_digits=5, decimal_places=2, default=0)
    breakdown = models.JSONField(_("Tarkib"), default=dict, blank=True)

    # --- Suniy intellekt tahlili ---
    ai_analysis = models.TextField(_("AI tahlili"), blank=True)
    ai_recommendation = models.TextField(_("AI tavsiyasi"), blank=True)
    ai_rating = models.CharField(_("AI bahosi"), max_length=20, blank=True)
    ai_generated = models.BooleanField(_("AI ishlatildi"), default=False)
    ai_model = models.CharField(_("AI model"), max_length=60, blank=True)

    status = models.CharField(_("Holat"), max_length=10, choices=STATUS_CHOICES, default='draft')
    computed_at = models.DateTimeField(_("Hisoblangan vaqt"), default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Oylik yozuvi")
        verbose_name_plural = _("Oylik yozuvlari")
        unique_together = ('period', 'employee')
        ordering = ['-period__year', '-period__month', 'employee__full_name']

    def __str__(self):
        return f"{self.employee.full_name} — {self.period.label} — {self.total_amount} so'm"

    @property
    def status_badge(self):
        return {'draft': 'warning', 'approved': 'info', 'paid': 'success'}.get(self.status, 'muted')

    def apply_breakdown(self, result):
        """engine.compute() natijasini yozuvga ko'chiradi."""
        self.base_amount = result['base_amount']
        self.hours_amount = result['hours_amount']
        self.students_amount = result['students_amount']
        self.kpi_bonus = result['kpi_bonus']
        self.penalties_amount = result['penalties_amount']
        self.gross_amount = result['gross_amount']
        self.total_amount = result['total_amount']
        self.kpi_score = result['kpi_score']
        self.breakdown = result['breakdown']
