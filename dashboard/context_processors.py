from django.conf import settings


def branding(request):
    """Har bir sahifaga brending va bildirishnoma sonini uzatadi.

    Markaz nomi/aloqa ma'lumotlari avval DB (CenterProfile) dan, bo'lmasa
    settings.py dagi qiymatlardan olinadi.
    """
    brand_name = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    center = None
    try:
        from .models import CenterProfile
        center = CenterProfile.objects.first()
        if center and center.name:
            brand_name = center.name
    except Exception:
        center = None

    ctx = {
        'BRAND_NAME': brand_name,
        'BRAND_COLOR': getattr(settings, 'BRAND_COLOR', '#D4640F'),
        'CENTER': center,
        'new_applications_count': 0,
    }
    ctx['pending_reset_count'] = 0
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and getattr(user, 'is_staff_role', False):
        try:
            from enrollments.models import RegistrationApplication
            ctx['new_applications_count'] = RegistrationApplication.objects.filter(
                status='new'
            ).count()
        except Exception:
            pass
        # Parol tiklash murojaatlari (faqat admin uchun)
        if user.is_superuser or getattr(user, 'role', '') == 'admin':
            try:
                from accounts.models import PasswordResetRequest
                ctx['pending_reset_count'] = PasswordResetRequest.objects.filter(
                    status='pending'
                ).count()
            except Exception:
                pass
    return ctx
