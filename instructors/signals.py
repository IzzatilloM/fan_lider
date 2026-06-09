from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Instructor

User = get_user_model()


@receiver(post_save, sender=User)
def sync_instructor_profile(sender, instance, created, **kwargs):
    """role='teacher' bo'lganda avtomatik o'qituvchi profili yaratiladi."""
    if instance.role == 'teacher':
        full_name = f"{instance.first_name or ''} {instance.last_name or ''}".strip()
        if not full_name:
            full_name = instance.username or instance.email
        Instructor.objects.update_or_create(
            user=instance,
            defaults={
                'full_name': full_name,
                'phone': instance.phone,
                'email': instance.email,
                'is_active': instance.is_active,
            },
        )
    else:
        Instructor.objects.filter(user=instance).delete()
