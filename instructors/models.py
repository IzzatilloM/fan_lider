from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Instructor(models.Model):
    """O'qituvchi profili."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='instructor_profile',
    )
    full_name = models.CharField(_("To'liq ism"), max_length=255)
    phone = models.CharField(_("Telefon"), max_length=20, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    specialty = models.CharField(_("Mutaxassislik"), max_length=255, blank=True, null=True)
    experience_years = models.PositiveIntegerField(_("Tajriba (yil)"), default=0)
    salary = models.DecimalField(_("Oylik (so'm)"), max_digits=12, decimal_places=2, default=0)
    bio = models.TextField(_("Bio"), blank=True, null=True)
    image = models.ImageField(_("Rasm"), upload_to='instructors/', blank=True, null=True)
    is_active = models.BooleanField(_("Faol"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = _("O'qituvchi")
        verbose_name_plural = _("O'qituvchilar")

    def __str__(self):
        return self.full_name

    @property
    def photo_url(self):
        if self.image:
            return self.image.url
        if self.user and self.user.google_picture:
            return self.user.google_picture
        return ''

    @property
    def active_groups(self):
        return self.courses.exclude(status='finished').count()
