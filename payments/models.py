from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

UZB_MONTHS = [
    _("Yanvar"), _("Fevral"), _("Mart"), _("Aprel"), _("May"), _("Iyun"),
    _("Iyul"), _("Avgust"), _("Sentabr"), _("Oktabr"), _("Noyabr"), _("Dekabr"),
]


class Invoice(models.Model):
    """Oylik to'lov hisob-fakturasi."""

    STATUS_CHOICES = (
        ('unpaid', _("To'lanmagan")),
        ('partial', _("Qisman to'langan")),
        ('paid', _("To'langan")),
        ('cancelled', _("Bekor qilingan")),
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='invoices',
        verbose_name=_("O'quvchi"),
    )
    enrollment = models.ForeignKey(
        'enrollments.Enrollment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices', verbose_name=_("Yozilish"),
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices', verbose_name=_("Guruh"),
    )

    year = models.PositiveIntegerField(_("Yil"), default=timezone.now().year)
    month = models.PositiveSmallIntegerField(_("Oy"), default=timezone.now().month)
    amount = models.DecimalField(_("Summa"), max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(_("To'langan"), max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(_("To'lov muddati"), null=True, blank=True)
    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='unpaid')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_invoices',
    )

    class Meta:
        verbose_name = _("Hisob-faktura")
        verbose_name_plural = _("Hisob-fakturalar")
        ordering = ['-year', '-month', '-created_at']
        unique_together = ('student', 'enrollment', 'year', 'month')

    def __str__(self):
        return f"{self.student} — {self.month_name} {self.year}"

    @property
    def month_name(self):
        if 1 <= self.month <= 12:
            return UZB_MONTHS[self.month - 1]
        return str(self.month)

    @property
    def remaining(self):
        return max(self.amount - self.paid_amount, Decimal('0'))

    @property
    def is_overdue(self):
        return self.status != 'paid' and self.due_date and self.due_date < timezone.now().date()

    def recalc(self, save=True):
        """To'lovlar asosida holatni qayta hisoblaydi."""
        total = self.payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')
        self.paid_amount = total
        if self.status != 'cancelled':
            if total <= 0:
                self.status = 'unpaid'
            elif total < self.amount:
                self.status = 'partial'
            else:
                self.status = 'paid'
        if save:
            super().save(update_fields=['paid_amount', 'status'])


class Payment(models.Model):
    """To'lov yozuvi (kassa)."""

    METHOD_CHOICES = (
        ('cash', _("Naqd")),
        ('card', _("Plastik karta")),
        ('click', _("Click")),
        ('payme', _("Payme")),
        ('transfer', _("Bank o'tkazmasi")),
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='payments',
        verbose_name=_("O'quvchi"),
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments', verbose_name=_("Hisob-faktura"),
    )
    amount = models.DecimalField(_("Summa"), max_digits=12, decimal_places=2)
    method = models.CharField(_("To'lov turi"), max_length=20, choices=METHOD_CHOICES, default='cash')
    paid_at = models.DateTimeField(_("To'lov vaqti"), default=timezone.now)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_payments', verbose_name=_("Qabul qildi"),
    )
    note = models.CharField(_("Izoh"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("To'lov")
        verbose_name_plural = _("To'lovlar")
        ordering = ['-paid_at']

    def __str__(self):
        return f"{self.student} — {self.amount} so'm"
