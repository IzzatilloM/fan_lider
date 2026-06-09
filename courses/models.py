from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Subject(models.Model):
    """O'quv yo'nalishi / fan (masalan: Matematika, Ingliz tili)."""

    name = models.CharField(_("Nomi"), max_length=120, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(_("Tavsif"), blank=True)
    color = models.CharField(_("Rang"), max_length=7, default='#D4640F')
    icon = models.CharField(_("Belgi (emoji)"), max_length=10, default='📘')
    is_active = models.BooleanField(_("Faol"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Yo'nalish")
        verbose_name_plural = _("Yo'nalishlar")
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    """O'quv guruhi — muayyan yo'nalish bo'yicha jadval va o'qituvchiga ega."""

    STATUS_CHOICES = (
        ('recruiting', _("Qabul ochiq")),
        ('ongoing', _("Davom etmoqda")),
        ('finished', _("Yakunlangan")),
        ('paused', _("Vaqtincha to'xtatilgan")),
    )

    WEEKDAY_CHOICES = (
        ('mon_wed_fri', _("Du-Chor-Juma")),
        ('tue_thu_sat', _("Se-Pay-Shan")),
        ('everyday', _("Har kuni")),
        ('weekend', _("Dam olish kunlari")),
    )

    name = models.CharField(_("Guruh nomi"), max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='courses',
        verbose_name=_("Yo'nalish"),
    )
    level = models.CharField(
        _("Daraja / level"), max_length=60, blank=True,
        help_text=_("Masalan: Beginner, Elementary, Intermediate, A1, B2 ..."),
    )
    teacher = models.ForeignKey(
        'instructors.Instructor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='courses', verbose_name=_("O'qituvchi"),
    )
    description = models.TextField(_("Tavsif"), blank=True)

    monthly_fee = models.DecimalField(
        _("Oylik to'lov (so'm)"), max_digits=12, decimal_places=2, default=0
    )
    duration_months = models.PositiveIntegerField(_("Davomiyligi (oy)"), default=3)
    capacity = models.PositiveIntegerField(_("Sig'im (max o'quvchi)"), default=15)

    weekdays = models.CharField(
        _("Dars kunlari"), max_length=20, choices=WEEKDAY_CHOICES, default='mon_wed_fri'
    )
    start_time = models.TimeField(_("Boshlanish vaqti"), null=True, blank=True)
    room = models.CharField(_("Xona"), max_length=50, blank=True)
    start_date = models.DateField(_("Boshlanish sanasi"), null=True, blank=True)

    status = models.CharField(
        _("Holat"), max_length=20, choices=STATUS_CHOICES, default='recruiting'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Guruh")
        verbose_name_plural = _("Guruhlar")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'guruh'
            slug = base
            i = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('courses:detail', kwargs={'slug': self.slug})

    @property
    def active_students_count(self):
        return self.enrollments.filter(status='active').count()

    @property
    def free_seats(self):
        return max(self.capacity - self.active_students_count, 0)

    @property
    def fill_percent(self):
        if not self.capacity:
            return 0
        return round(self.active_students_count / self.capacity * 100)

    @property
    def is_full(self):
        return self.active_students_count >= self.capacity
