from django.db import models


class CenterProfile(models.Model):
    """O'quv markazi haqida tahrirlanadigan ma'lumotlar (yagona yozuv — singleton).

    Admin "Sozlamalar" sahifasida tahrir qiladi. Brending context_processor
    shu yerdan o'qiydi (bo'lmasa settings.py dagi qiymatlarga tayanadi).
    """

    name = models.CharField("Markaz nomi", max_length=120, default='Fan Lider')
    tagline = models.CharField(
        "Shior / qisqa tavsif", max_length=200, blank=True,
        default="O'quv markazi boshqaruv tizimi",
    )
    phone = models.CharField("Telefon", max_length=40, blank=True, default='+998 90 000 00 00')
    email = models.EmailField("Email", blank=True, default='')
    address = models.CharField("Manzil", max_length=255, blank=True, default='Toshkent sh.')
    working_hours = models.CharField(
        "Ish vaqti", max_length=120, blank=True,
        default="Dushanba–Shanba, 09:00–19:00",
    )
    about = models.TextField("Markaz haqida", blank=True, default='')
    telegram_bot_username = models.CharField(
        "Telegram bot (@siz)", max_length=64, blank=True, default='',
        help_text="Masalan: fan_lider_crm_bot",
    )
    logo = models.ImageField("Logo", upload_to='center/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Markaz ma'lumotlari"
        verbose_name_plural = "Markaz ma'lumotlari"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Yagona yozuv bo'lishini ta'minlaymiz
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
