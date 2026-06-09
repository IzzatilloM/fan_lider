"""O'quvchi kabineti logini bilan ishlash — bir nechta joyda qayta ishlatiladi.

`student_login_create` view ham, ariza tasdiqlash (enrollments.application_convert)
ham shu yerdagi funksiyalardan foydalanadi.
"""
import secrets

from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


def suggest_username(student):
    """O'quvchi uchun band bo'lmagan login (username) tavsiya qiladi."""
    base = (slugify(f"{student.first_name}{student.last_name}") or 'student').replace('-', '')
    base = base[:20] or 'student'
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base}{i}"
    return username


def create_or_reset_login(student, username='', password=''):
    """O'quvchi uchun kabinet loginini yaratadi yoki parolini yangilaydi.

    `username`/`password` bo'sh bo'lsa — avtomatik generatsiya qilinadi.
    (username, password, created) qaytaradi; `created` — yangi login bo'lsa True.
    Username bandligini o'zi hal qiladi (band bo'lsa avtomatik unikal nom).
    """
    username = (username or '').strip()
    password = (password or '').strip() or secrets.token_urlsafe(6)

    if student.user_id:
        user = student.user
        if username and username != user.username:
            # Yangi username so'ralgan — band bo'lsa unikal qilamiz
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = suggest_username(student)
        elif not username:
            username = user.username
        user.username = username
        user.set_password(password)
        user.plain_password = password
        user.role = 'student'
        user.is_staff = False
        user.is_superuser = False
        user.save()
        return username, password, False

    # Yangi login
    if not username or User.objects.filter(username=username).exists():
        username = suggest_username(student)
    user = User.objects.create_user(
        username=username, password=password, role='student',
        first_name=student.first_name, last_name=student.last_name,
        email=student.email or '', plain_password=password,
    )
    student.user = user
    student.save(update_fields=['user'])
    return username, password, True
