"""Fan Lider Telegram bot — webhook mantiq (PythonAnywhere bepul uchun mos).

Professional, ko'p bosqichli bot:
  • Doimiy pastki (reply) menyu + boy inline navigatsiya.
  • Yo'nalish → guruh → guruh tafsiloti → aniq guruhga yozilish.
  • Ro'yxatdan o'tish FSM: ism → telefon (kontakt tugmasi) → yosh (ixtiyoriy).
    Ariza tizimga ANIQ tanlangan guruh (preferred_course) bilan tushadi.
  • "Mening arizalarim" — holatini ko'rsatadi (chat_id bo'yicha).
  • Markaz haqida, Aloqa.

Admin arizani tasdiqlaganda (enrollments.application_convert) —
cabinet.telegram.notify_student_credentials o'sha chat_id ga kabinet
havolasi + login + parolni yuboradi.
"""
import logging

import requests
from django.conf import settings

from courses.models import Course, Subject
from enrollments.models import RegistrationApplication

from .models import BotChatState

logger = logging.getLogger(__name__)

# --- Doimiy pastki menyu tugmalari (matn sifatida keladi) ---------------- #
B_COURSES = "📚 Kurslar"
B_REGISTER = "📝 Ro'yxatdan o'tish"
B_MYAPPS = "🎓 Mening arizalarim"
B_ABOUT = "ℹ️ Markaz haqida"
B_CONTACT = "📞 Aloqa"
B_PWRESET = "🔑 Parolni tiklash"
B_MYID = "🆔 ID raqamim"


# ======================================================================== #
#  Telegram API past darajadagi funksiyalar
# ======================================================================== #
def _api(method):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    return f"https://api.telegram.org/bot{token}/{method}"


def _post(method, payload):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None
    try:
        r = requests.post(_api(method), json=payload, timeout=10)
        return r.json()
    except Exception:
        logger.exception("Telegram %s xatolik", method)
        return None


def send(chat_id, text, inline=None, reply_kb=None, contact_btn=False):
    """Xabar yuboradi.

    inline      — inline tugmalar (ro'yxat ko'rinishida) yoki None
    reply_kb    — pastki doimiy klaviatura (True bo'lsa asosiy menyu)
    contact_btn — telefon ulashish tugmasi (ro'yxatdan o'tishda)
    """
    payload = {
        'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    if inline is not None:
        payload['reply_markup'] = {'inline_keyboard': inline}
    elif contact_btn:
        payload['reply_markup'] = {
            'keyboard': [
                [{'text': "📱 Telefon raqamni yuborish", 'request_contact': True}],
                [{'text': "🚫 Bekor qilish"}],
            ],
            'resize_keyboard': True, 'one_time_keyboard': True,
        }
    elif reply_kb:
        payload['reply_markup'] = _main_reply_kb()
    return _post('sendMessage', payload)


def _edit(chat_id, message_id, text, inline=None):
    """Mavjud xabarni tahrirlaydi (inline navigatsiya silliq bo'lishi uchun)."""
    payload = {
        'chat_id': chat_id, 'message_id': message_id, 'text': text,
        'parse_mode': 'HTML', 'disable_web_page_preview': True,
    }
    if inline is not None:
        payload['reply_markup'] = {'inline_keyboard': inline}
    res = _post('editMessageText', payload)
    if not res or not res.get('ok'):
        # Tahrir imkonsiz bo'lsa (masalan, kontent bir xil) — yangi xabar
        send(chat_id, text, inline=inline)


def _answer_callback(cb_id, text=''):
    _post('answerCallbackQuery', {'callback_query_id': cb_id, 'text': text})


# ======================================================================== #
#  Klaviaturalar
# ======================================================================== #
def _main_reply_kb():
    return {
        'keyboard': [
            [{'text': B_COURSES}, {'text': B_REGISTER}],
            [{'text': B_MYAPPS}, {'text': B_ABOUT}],
            [{'text': B_CONTACT}, {'text': B_PWRESET}],
            [{'text': B_MYID}],
        ],
        'resize_keyboard': True,
    }


def _home_inline():
    return [
        [{'text': "📚 Kurslar / guruhlar", 'callback_data': 'subjects:browse'}],
        [{'text': "📝 Ro'yxatdan o'tish", 'callback_data': 'reg_start'}],
        [{'text': "ℹ️ Markaz haqida", 'callback_data': 'about'},
         {'text': "📞 Aloqa", 'callback_data': 'contact'}],
        [{'text': "🎓 Mening arizalarim", 'callback_data': 'myapps'}],
        [{'text': "🔑 Parolni tiklash", 'callback_data': 'pwreset'}],
    ]


def _back_home_inline():
    return [[{'text': "⬅️ Bosh menyu", 'callback_data': 'home'}]]


# ======================================================================== #
#  Matnlar
# ======================================================================== #
def _center():
    """Markaz ma'lumotlari (DB) — bo'lmasa None."""
    try:
        from dashboard.models import CenterProfile
        return CenterProfile.objects.first()
    except Exception:
        return None


def _brand():
    c = _center()
    if c and c.name:
        return c.name
    return getattr(settings, 'BRAND_NAME', 'Fan Lider')


def _welcome(name=''):
    brand = _brand()
    salom = f", {name}" if name else ""
    return (
        f"🎓 <b>{brand} o'quv markazi</b>ga xush kelibsiz{salom}!\n\n"
        f"Bu yerda siz:\n"
        f"• 📚 faol kurslar va guruhlar bilan tanishasiz,\n"
        f"• 📝 to'g'ridan-to'g'ri kerakli guruhga yozilasiz,\n"
        f"• 🎓 arizangiz holatini kuzatasiz,\n"
        f"• 📞 markaz bilan bog'lanasiz.\n\n"
        f"Quyidagi menyudan tanlang 👇"
    )


def _about():
    brand = _brand()
    c = _center()
    if c and c.about:
        return f"ℹ️ <b>{brand} o'quv markazi haqida</b>\n\n{c.about}"
    return (
        f"ℹ️ <b>{brand} o'quv markazi haqida</b>\n\n"
        f"Bizning maqsadimiz — har bir o'quvchining bilimini real natijaga aylantirish.\n\n"
        f"✅ Tajribali o'qituvchilar va isbotlangan metodika\n"
        f"✅ Kichik guruhlar — har bir o'quvchiga individual e'tibor\n"
        f"✅ Qulay jadval va zamonaviy auditoriyalar\n"
        f"✅ Doimiy monitoring: davomat, baholar, hisobotlar\n"
        f"✅ Har bir o'quvchiga <b>shaxsiy onlayn kabinet</b>\n\n"
        f"📝 Ro'yxatdan o'tish uchun pastdagi menyudan foydalaning."
    )


def _my_id_text(chat_id):
    brand = _brand()
    return (
        f"🆔 <b>Sizning Telegram ID raqamingiz:</b>\n\n"
        f"<code>{chat_id}</code>\n\n"
        f"👤 <b>Administrator yoki Direktor</b> sifatida {brand} CRM tizimiga "
        f"ro'yxatdan o'tish uchun shu raqamni saytdagi <b>«Telegram ID»</b> maydoniga "
        f"kiriting. Tasdiqlash kodi aynan shu chatga keladi.\n\n"
        f"ℹ️ Raqamni nusxalash uchun ustiga bosing."
    )


def _contact():
    brand = _brand()
    c = _center()
    phone = (c.phone if c and c.phone else getattr(settings, 'CENTER_PHONE', '+998 90 000 00 00'))
    addr = (c.address if c and c.address else getattr(settings, 'CENTER_ADDRESS', "Toshkent sh."))
    hours = (c.working_hours if c and c.working_hours else "Dushanba–Shanba, 09:00–19:00")
    return (
        f"📞 <b>{brand} bilan bog'lanish</b>\n\n"
        f"☎️ Telefon: {phone}\n"
        f"📍 Manzil: {addr}\n"
        f"🕘 Ish vaqti: {hours}\n\n"
        f"Savolingizni shu yerga yozib qoldiring — administrator javob beradi."
    )


def _fmt_fee(value):
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (TypeError, ValueError):
        return "0"


def _weekday(course):
    try:
        return course.get_weekdays_display()
    except Exception:
        return "—"


# ======================================================================== #
#  Kurslar navigatsiyasi (yo'nalish → guruh → tafsilot → yozilish)
# ======================================================================== #
def _subjects_with_courses():
    """Faol guruhga ega yo'nalishlar ro'yxati."""
    course_qs = Course.objects.filter(status__in=['recruiting', 'ongoing'])
    subject_ids = list(course_qs.values_list('subject_id', flat=True).distinct())
    return Subject.objects.filter(id__in=subject_ids, is_active=True).order_by('name')


def _subjects_view(mode='browse'):
    """Yo'nalishlar inline ro'yxati. mode='reg' bo'lsa yozilish konteksti."""
    subjects = list(_subjects_with_courses())
    if not subjects:
        return ("Hozircha faol guruhlar yo'q. Tez orada yangilanadi. 🔄",
                _back_home_inline())
    title = (
        "📝 <b>Ro'yxatdan o'tish</b>\n\nAvval <b>yo'nalishni</b> tanlang:"
        if mode == 'reg' else
        "📚 <b>Yo'nalishlar</b>\n\nQiziqqan yo'nalishingizni tanlang:"
    )
    rows = []
    for s in subjects:
        n = Course.objects.filter(subject=s, status__in=['recruiting', 'ongoing']).count()
        rows.append([{
            'text': f"{s.icon} {s.name} ({n})",
            'callback_data': f"subj:{s.id}:{mode}",
        }])
    rows.append([{'text': "⬅️ Bosh menyu", 'callback_data': 'home'}])
    return title, rows


def _courses_in_subject_view(subject_id, mode='browse'):
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return ("Yo'nalish topilmadi.", _back_home_inline())
    courses = list(
        Course.objects.filter(subject=subject, status__in=['recruiting', 'ongoing'])
        .select_related('teacher')
    )
    if not courses:
        return (f"{subject.icon} <b>{subject.name}</b>\n\nHozircha faol guruh yo'q.",
                [[{'text': "⬅️ Yo'nalishlar", 'callback_data': f'subjects:{mode}'}]])
    title = (
        f"{subject.icon} <b>{subject.name}</b> — guruhlar\n\n"
        f"Guruhni tanlang (tafsilot va yozilish uchun):"
    )
    rows = []
    for c in courses:
        seats = "to'lgan" if c.is_full else f"{c.free_seats} joy"
        rows.append([{
            'text': f"{c.name} · {_fmt_fee(c.monthly_fee)} so'm · {seats}",
            'callback_data': f"course:{c.id}:{mode}",
        }])
    rows.append([{'text': "⬅️ Yo'nalishlar", 'callback_data': f'subjects:{mode}'}])
    return title, rows


def _course_detail_view(course_id, mode='browse'):
    try:
        course = Course.objects.select_related('subject', 'teacher').get(id=course_id)
    except Course.DoesNotExist:
        return ("Guruh topilmadi.", _back_home_inline(), None)
    icon = course.subject.icon if course.subject_id else '📘'
    teacher = course.teacher.full_name if course.teacher_id else "—"
    time = course.start_time.strftime('%H:%M') if course.start_time else "—"
    level = f"\n📊 Daraja: {course.level}" if course.level else ""
    seats = ("⛔️ Joylar to'lgan (navbatga yozilasiz)" if course.is_full
             else f"✅ Bo'sh joylar: {course.free_seats} / {course.capacity}")
    desc = f"\n\n<i>{course.description}</i>" if course.description else ""
    text = (
        f"{icon} <b>{course.name}</b>\n"
        f"<i>{course.subject.name}</i>{level}\n\n"
        f"👨‍🏫 O'qituvchi: {teacher}\n"
        f"🗓 Kunlar: {_weekday(course)}\n"
        f"⏰ Vaqti: {time}\n"
        f"⏳ Davomiyligi: {course.duration_months} oy\n"
        f"💰 Oylik to'lov: <b>{_fmt_fee(course.monthly_fee)} so'm</b>\n"
        f"{seats}{desc}"
    )
    rows = [
        [{'text': "✅ Shu guruhga yozilish", 'callback_data': f"reg:{course.id}"}],
        [{'text': "⬅️ Guruhlar", 'callback_data': f"subj:{course.subject_id}:{mode}"},
         {'text': "🏠 Bosh menyu", 'callback_data': 'home'}],
    ]
    return text, rows, course


# ======================================================================== #
#  Mening arizalarim
# ======================================================================== #
def _my_apps_text(chat_id):
    apps = list(
        RegistrationApplication.objects
        .filter(telegram_chat_id=str(chat_id))
        .select_related('preferred_course', 'subject')
        .order_by('-created_at')[:5]
    )
    if not apps:
        return ("🎓 <b>Mening arizalarim</b>\n\n"
                "Sizda hali ariza yo'q. 📝 «Ro'yxatdan o'tish» orqali ariza qoldiring.")
    lines = ["🎓 <b>Mening arizalarim</b>\n"]
    status_emoji = {'new': '🆕', 'contacted': '📞', 'trial': '🧪',
                    'enrolled': '✅', 'rejected': '❌'}
    for a in apps:
        course = a.preferred_course.name if a.preferred_course_id else (
            a.subject.name if a.subject_id else "—")
        em = status_emoji.get(a.status, '•')
        lines.append(
            f"\n{em} <b>{course}</b>\n"
            f"   Holat: {a.get_status_display()}\n"
            f"   Sana: {a.created_at:%d.%m.%Y}"
        )
    lines.append("\n\nTasdiqlangach — kabinet havolasi va parol shu yerga yuboriladi. 🔑")
    return "".join(lines)


# ======================================================================== #
#  Parolni tiklash (o'qituvchi / o'quvchi → adminga murojaat)
# ======================================================================== #
def _pwreset_menu():
    text = (
        "🔑 <b>Parolni tiklash</b>\n\n"
        "O'qituvchi va o'quvchilar parolini administrator tiklaydi.\n"
        "Kim ekaningizni tanlang — so'ng loginingizni yuborasiz va "
        "murojaat administratorga tushadi."
    )
    rows = [
        [{'text': "👨‍🏫 O'qituvchi", 'callback_data': 'pwrole:teacher'}],
        [{'text': "🎓 O'quvchi", 'callback_data': 'pwrole:student'}],
        [{'text': "⬅️ Bosh menyu", 'callback_data': 'home'}],
    ]
    return text, rows


def _start_pwreset(chat_id, role):
    state = _state(chat_id)
    state.step = 'pwreset_login'
    state.data = {'pwreset_role': role}
    state.save()
    role_label = "o'qituvchi" if role == 'teacher' else "o'quvchi"
    send(
        chat_id,
        f"🔑 <b>Parolni tiklash — {role_label}</b>\n\n"
        f"Iltimos, tizimdagi <b>loginingizni</b> (yoki ro'yxatdan o'tgan "
        f"telefon raqamingizni) yuboring:",
    )


def _finish_pwreset(chat_id, state, identifier):
    from accounts.models import PasswordResetRequest

    data = state.data or {}
    role = data.get('pwreset_role', 'student')
    req = PasswordResetRequest.objects.create(
        role=role,
        identifier=identifier[:150],
        telegram_chat_id=str(chat_id),
    )
    # Mos foydalanuvchini avtomatik topishga urinamiz
    user = req.find_user()
    if user is not None:
        req.matched_user = user
        if not user.first_name and not req.full_name:
            req.full_name = user.get_full_name()
        req.save(update_fields=['matched_user', 'full_name'])
    _reset(state)
    send(
        chat_id,
        "✅ <b>Murojaatingiz yuborildi!</b>\n\n"
        "Administrator parolingizni tekshirib, yangi parol o'rnatadi. "
        "Yangi parolingiz aynan shu botga yuboriladi. 🔔\n\n"
        "Iltimos, kuting. 🙏",
        reply_kb=True,
    )


# ======================================================================== #
#  FSM holati
# ======================================================================== #
def _state(chat_id):
    obj, _ = BotChatState.objects.get_or_create(chat_id=str(chat_id))
    return obj


def _reset(state):
    state.step = ''
    state.data = {}
    state.save()


def _start_registration(chat_id, course):
    state = _state(chat_id)
    state.step = 'reg_name'
    state.data = {
        'course_id': course.id,
        'course_name': course.name,
        'subject_id': course.subject_id,
    }
    state.save()
    send(
        chat_id,
        f"📝 <b>{course.name}</b> guruhiga ro'yxatdan o'tish.\n\n"
        f"1/3 — Iltimos, <b>ism va familiyangizni</b> to'liq yozing:",
    )


def _start_registration_form(chat_id):
    """«Ro'yxatdan o'tish» bosilganda — kurslar emas, to'g'ridan-to'g'ri forma."""
    state = _state(chat_id)
    state.step = 'reg_name'
    state.data = {}
    state.save()
    send(
        chat_id,
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Bir necha qadamda ma'lumotlaringizni qoldiring — administrator siz bilan "
        "bog'lanib, shaxsiy kabinetingizni ochadi.\n\n"
        "1/3 — Iltimos, <b>ism va familiyangizni</b> to'liq yozing:",
    )


def _finish_registration(chat_id, state, age=None):
    data = state.data or {}
    full_name = data.get('full_name', "Noma'lum")
    phone = data.get('phone', '')
    course = None
    if data.get('course_id'):
        course = Course.objects.filter(id=data['course_id']).first()

    RegistrationApplication.objects.create(
        full_name=full_name[:200],
        phone=phone[:20],
        age=age,
        subject_id=data.get('subject_id') or (course.subject_id if course else None),
        preferred_course=course,
        source='telegram',
        telegram_chat_id=str(chat_id),
        message="Telegram bot orqali ro'yxatdan o'tdi.",
    )
    _reset(state)

    course_line = f"📚 Guruh: <b>{course.name}</b>\n" if course else ""
    age_line = f"🎂 Yosh: {age}\n" if age else ""
    send(
        chat_id,
        f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
        f"{course_line}"
        f"👤 F.I.O: {full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"{age_line}\n"
        f"Markaz ma'muriyati tez orada siz bilan bog'lanadi. "
        f"Tasdiqlangach — <b>shaxsiy kabinet havolasi, login va parol</b> "
        f"aynan shu botga yuboriladi. Rahmat! 🙏",
        reply_kb=True,
    )


# ======================================================================== #
#  Asosiy update ishlovchisi
# ======================================================================== #
def handle_update(update):
    cb = update.get('callback_query')
    if cb:
        _handle_callback(cb)
        return
    msg = update.get('message')
    if msg:
        _handle_message(msg)


# ----------------------------- Inline tugmalar -------------------------- #
def _handle_callback(cb):
    chat_id = cb['message']['chat']['id']
    message_id = cb['message']['message_id']
    data = cb.get('data', '')
    _answer_callback(cb['id'])
    parts = data.split(':')
    head = parts[0]

    if head == 'home':
        # Inline ro'yxatni yopamiz — asosiy menyu doimiy pastki klaviaturada turadi
        _edit(chat_id, message_id,
              "🏠 <b>Bosh menyu</b>\n\nQuyidagi pastki tugmalardan foydalaning 👇",
              inline=[])
    elif head == 'about':
        _edit(chat_id, message_id, _about(), inline=_back_home_inline())
    elif head == 'contact':
        _edit(chat_id, message_id, _contact(), inline=_back_home_inline())
    elif head == 'myapps':
        _edit(chat_id, message_id, _my_apps_text(chat_id), inline=_back_home_inline())
    elif head == 'subjects':
        mode = parts[1] if len(parts) > 1 else 'browse'
        text, inline = _subjects_view(mode)
        _edit(chat_id, message_id, text, inline=inline)
    elif head == 'subj':
        sid = parts[1]
        mode = parts[2] if len(parts) > 2 else 'browse'
        text, inline = _courses_in_subject_view(sid, mode)
        _edit(chat_id, message_id, text, inline=inline)
    elif head == 'course':
        cid = parts[1]
        mode = parts[2] if len(parts) > 2 else 'browse'
        text, inline, _course = _course_detail_view(cid, mode)
        _edit(chat_id, message_id, text, inline=inline)
    elif head == 'reg_start':
        _start_registration_form(chat_id)
    elif head == 'reg':
        course = Course.objects.filter(id=parts[1]).first()
        if not course:
            _edit(chat_id, message_id, "Guruh topilmadi.", inline=_back_home_inline())
            return
        _start_registration(chat_id, course)
    elif head == 'skip_age':
        state = _state(chat_id)
        if state.step == 'reg_age':
            _finish_registration(chat_id, state, age=None)
    elif head == 'pwreset':
        text, inline = _pwreset_menu()
        _edit(chat_id, message_id, text, inline=inline)
    elif head == 'pwrole':
        role = parts[1] if len(parts) > 1 else 'student'
        _start_pwreset(chat_id, role)


# ------------------------------ Xabarlar -------------------------------- #
def _handle_message(msg):
    chat_id = msg['chat']['id']
    text = (msg.get('text') or '').strip()
    contact = msg.get('contact')
    first_name = (msg.get('from') or {}).get('first_name', '')
    low = text.lower()

    # --- Bekor qilish istalgan paytda ---
    if text == "🚫 Bekor qilish" or low in ('/cancel', 'bekor'):
        _reset(_state(chat_id))
        send(chat_id, "❌ Bekor qilindi. Quyidagi menyudan davom eting 👇", reply_kb=True)
        return

    # --- Buyruqlar va doimiy menyu tugmalari ---
    if text in ('/start', '/menu') or low in ('start', 'menyu', 'menu'):
        _reset(_state(chat_id))
        send(chat_id, _welcome(first_name), reply_kb=True)
        return
    if text == B_COURSES or text == '/kurslar' or low == 'kurslar':
        t, kb = _subjects_view('browse')
        send(chat_id, t, inline=kb)
        return
    if text == B_REGISTER or text == '/royxat' or low == 'royxat':
        _start_registration_form(chat_id)
        return
    if text == B_MYAPPS or text == '/arizalarim':
        send(chat_id, _my_apps_text(chat_id), inline=_back_home_inline())
        return
    if text == B_ABOUT or text == '/about':
        send(chat_id, _about(), inline=_back_home_inline())
        return
    if text == B_CONTACT or text == '/aloqa' or low == 'aloqa':
        send(chat_id, _contact(), inline=_back_home_inline())
        return
    if text == B_PWRESET or text == '/parol' or low == 'parol':
        t, kb = _pwreset_menu()
        send(chat_id, t, inline=kb)
        return
    if text == B_MYID or text in ('/id', '/myid') or low in ('id', 'myid'):
        send(chat_id, _my_id_text(chat_id), inline=_back_home_inline())
        return

    # --- FSM bosqichlari ---
    state = _state(chat_id)

    if state.step == 'pwreset_login':
        if len(text) < 3:
            send(chat_id, "Iltimos, to'g'ri <b>login</b> yoki <b>telefon</b> yuboring:")
            return
        _finish_pwreset(chat_id, state, text.strip())
        return

    if state.step == 'reg_name':
        if len(text) < 3:
            send(chat_id, "Iltimos, to'liq <b>ism va familiyangizni</b> yozing:")
            return
        state.data['full_name'] = text[:200]
        state.step = 'reg_phone'
        state.save()
        send(
            chat_id,
            f"Rahmat, {text.split()[0]}! 🙌\n\n"
            f"2/3 — Endi <b>telefon raqamingizni</b> yuboring "
            f"(pastdagi tugma orqali yoki qo'lda, masalan +998901234567):",
            contact_btn=True,
        )
        return

    if state.step == 'reg_phone':
        phone = contact['phone_number'] if contact else text
        phone = (phone or '').strip()
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) < 7:
            send(chat_id, "To'g'ri telefon raqam yuboring (masalan +998901234567):",
                 contact_btn=True)
            return
        state.data['phone'] = phone
        state.step = 'reg_age'
        state.save()
        send(
            chat_id,
            "3/3 — O'quvchining <b>yoshini</b> raqamda yozing (masalan: 14).\n"
            "Agar ko'rsatishni xohlamasangiz — «O'tkazib yuborish».",
            inline=[[{'text': "⏭ O'tkazib yuborish", 'callback_data': 'skip_age'}]],
        )
        return

    if state.step == 'reg_age':
        digits = ''.join(ch for ch in text if ch.isdigit())
        if not digits:
            send(chat_id, "Yoshni raqamda yozing (masalan: 14) yoki «O'tkazib yuborish» tugmasini bosing.",
                 inline=[[{'text': "⏭ O'tkazib yuborish", 'callback_data': 'skip_age'}]])
            return
        age = min(int(digits), 120)
        _finish_registration(chat_id, state, age=age)
        return

    # --- Holatsiz har qanday xabar — bosh menyu (faqat pastki klaviatura) ---
    send(chat_id, _welcome(first_name), reply_kb=True)
