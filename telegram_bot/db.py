"""Django ORM bilan ishlash (async wrapperlar).

aiogram async, Django ORM sync — shuning uchun sync_to_async ishlatamiz.
Kurslar/yo'nalishlar matni va tugmalari webhook bot (`cabinet.bot`) dan
qayta ishlatiladi — kontent bitta joyda turadi.
"""
from asgiref.sync import sync_to_async

from cabinet import bot as wb

# Webhook botdagi tayyor "view" funksiyalari (text, inline_rows) qaytaradi
subjects_view = sync_to_async(wb._subjects_view)
courses_in_subject_view = sync_to_async(wb._courses_in_subject_view)
my_apps_text = sync_to_async(wb._my_apps_text)


@sync_to_async
def course_detail(course_id):
    """(text, inline_rows) — guruh tafsiloti."""
    text, rows, _course = wb._course_detail_view(course_id)
    return text, rows


@sync_to_async
def get_course_brief(course_id):
    """Ro'yxatdan o'tishni boshlash uchun: (id, name, subject_id) yoki None."""
    from courses.models import Course
    c = Course.objects.filter(id=course_id).only('id', 'name', 'subject').first()
    if not c:
        return None
    return {'id': c.id, 'name': c.name, 'subject_id': c.subject_id}


@sync_to_async
def create_application(full_name, phone, age, course_id, subject_id, chat_id):
    from courses.models import Course
    from enrollments.models import RegistrationApplication
    course = Course.objects.filter(id=course_id).first() if course_id else None
    return RegistrationApplication.objects.create(
        full_name=full_name[:200],
        phone=phone[:20],
        age=age,
        subject_id=subject_id or (course.subject_id if course else None),
        preferred_course=course,
        source='telegram',
        telegram_chat_id=str(chat_id),
        message="Telegram bot orqali ro'yxatdan o'tdi.",
    )


# Parolni tiklash menyusi (text, inline_rows) — webhook botdan qayta ishlatamiz
pwreset_menu = sync_to_async(wb._pwreset_menu)


@sync_to_async
def create_pwreset_request(chat_id, role, identifier):
    """O'qituvchi/o'quvchining parol tiklash murojaatini yaratadi.

    Murojaat admin panelidagi «Parol murojaatlari» bo'limiga tushadi.
    Admin yangi parol o'rnatsa — bot foydalanuvchiga yangi parolni yuboradi.
    """
    from accounts.models import PasswordResetRequest
    req = PasswordResetRequest.objects.create(
        role=role,
        identifier=identifier[:150],
        telegram_chat_id=str(chat_id),
    )
    user = req.find_user()
    if user is not None:
        req.matched_user = user
        if not user.first_name and not req.full_name:
            req.full_name = user.get_full_name()
        req.save(update_fields=['matched_user', 'full_name'])
    return True
