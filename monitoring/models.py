from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Attendance(models.Model):
    """O'quvchi davomati."""

    STATUS_CHOICES = (
        ('present', _("Keldi")),
        ('absent', _("Kelmadi")),
        ('late', _("Kechikdi")),
        ('excused', _("Sababli")),
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='attendances',
        verbose_name=_("O'quvchi"),
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='attendances',
        verbose_name=_("Guruh"),
    )
    date = models.DateField(_("Sana"), default=timezone.now)
    status = models.CharField(_("Holat"), max_length=20, choices=STATUS_CHOICES, default='present')
    note = models.CharField(_("Izoh"), max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_attendances',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Davomat")
        verbose_name_plural = _("Davomat")
        unique_together = ('student', 'course', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} — {self.date} — {self.get_status_display()}"

    @property
    def is_present(self):
        return self.status in ('present', 'late')


class Assessment(models.Model):
    """O'quvchining bahosi / imtihon natijasi."""

    TYPE_CHOICES = (
        ('lesson', _("Joriy baho")),
        ('homework', _("Uy ishi")),
        ('quiz', _("Test / Quiz")),
        ('exam', _("Imtihon")),
        ('oral', _("Og'zaki")),
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='assessments',
        verbose_name=_("O'quvchi"),
    )
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='assessments',
        verbose_name=_("Guruh"),
    )
    type = models.CharField(_("Turi"), max_length=20, choices=TYPE_CHOICES, default='lesson')
    title = models.CharField(_("Nomi"), max_length=200, blank=True)
    date = models.DateField(_("Sana"), default=timezone.now)
    score = models.DecimalField(_("Ball"), max_digits=6, decimal_places=2, default=0)
    max_score = models.DecimalField(_("Maksimal ball"), max_digits=6, decimal_places=2, default=100)
    percentage = models.DecimalField(_("Foiz"), max_digits=5, decimal_places=2, default=0)
    comment = models.CharField(_("Izoh"), max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recorded_assessments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Baho")
        verbose_name_plural = _("Baholar")
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if self.max_score and self.max_score > 0:
            self.percentage = round(self.score / self.max_score * 100, 2)
        else:
            self.percentage = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} — {self.title or self.get_type_display()} — {self.percentage}%"

    @property
    def grade_5(self):
        """100 ballik foizni 5 ballik bahoga aylantiradi."""
        p = float(self.percentage)
        if p >= 86:
            return 5
        if p >= 71:
            return 4
        if p >= 56:
            return 3
        return 2

    @property
    def badge_class(self):
        p = float(self.percentage)
        if p >= 86:
            return 'success'
        if p >= 56:
            return 'warning'
        return 'danger'


class Lesson(models.Model):
    """O'tilgan dars mavzusi (o'quv jarayoni jurnali)."""

    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='lessons',
        verbose_name=_("Guruh"),
    )
    date = models.DateField(_("Sana"), default=timezone.now)
    topic = models.CharField(_("Mavzu"), max_length=255)
    description = models.TextField(_("Tavsif"), blank=True)
    homework = models.TextField(_("Uyga vazifa"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Dars")
        verbose_name_plural = _("Darslar jurnali")
        ordering = ['-date']

    def __str__(self):
        return f"{self.course} — {self.date} — {self.topic}"
