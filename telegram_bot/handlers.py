"""Bot handlerlari (aiogram 3.x router).

Kontent (matnlar + inline tugmalar) webhook bot (`cabinet.bot`) bilan bitta
manbadan olinadi. Bu yerda faqat aiogram navigatsiyasi va ro'yxatdan o'tish
FSM (ism → telefon → yosh) joylashgan. Ariza ANIQ tanlangan guruh bilan
tizimga tushadi.
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from cabinet import bot as wb

from . import db
from . import keyboards as kb

router = Router()


class Reg(StatesGroup):
    """Ro'yxatdan o'tish bosqichlari."""
    name = State()
    phone = State()
    age = State()


class PwReset(StatesGroup):
    """Parolni tiklash — login so'rash bosqichi."""
    login = State()


async def _safe_edit(cb: CallbackQuery, text, rows):
    """Inline xabarni tahrirlaydi; imkonsiz bo'lsa yangi xabar yuboradi."""
    markup = kb.to_inline(rows)
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except Exception:
        await cb.message.answer(text, reply_markup=markup)


# ====================================================================== #
#  Buyruqlar va doimiy menyu tugmalari
# ====================================================================== #
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(wb._welcome(message.from_user.first_name or ""),
                         reply_markup=kb.main_menu())


async def show_courses(message: Message):
    text, rows = await db.subjects_view('browse')
    await message.answer(text, reply_markup=kb.to_inline(rows))


async def show_register(message: Message, state: FSMContext):
    # «Ro'yxatdan o'tish» bosilganda — kurslar emas, to'g'ridan-to'g'ri forma.
    await _start_reg_form(message, state)


async def _start_reg_form(message: Message, state: FSMContext):
    """Ro'yxatdan o'tish formasini boshlaydi (kurs tanlashsiz)."""
    await state.set_state(Reg.name)
    await state.update_data(course_id=None, subject_id=None, course_name=None)
    await message.answer(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Bir necha qadamda ma'lumotlaringizni qoldiring — administrator siz bilan "
        "bog'lanib, shaxsiy kabinetingizni ochadi.\n\n"
        "1/3 — Iltimos, <b>ism va familiyangizni</b> to'liq yozing:",
        reply_markup=kb.cancel_only(),
    )


async def show_pwreset(message: Message):
    text, rows = await db.pwreset_menu()
    await message.answer(text, reply_markup=kb.to_inline(rows))


async def show_myapps(message: Message):
    text = await db.my_apps_text(message.chat.id)
    await message.answer(text, reply_markup=kb.to_inline(wb._back_home_inline()))


async def show_about(message: Message):
    await message.answer(wb._about(), reply_markup=kb.to_inline(wb._back_home_inline()))


async def show_contact(message: Message):
    await message.answer(wb._contact(), reply_markup=kb.to_inline(wb._back_home_inline()))


router.message.register(show_courses, F.text == wb.B_COURSES)
router.message.register(show_courses, Command("kurslar"))
router.message.register(show_register, F.text == wb.B_REGISTER)
router.message.register(show_register, Command("royxat"))
router.message.register(show_myapps, F.text == wb.B_MYAPPS)
router.message.register(show_myapps, Command("arizalarim"))
router.message.register(show_about, F.text == wb.B_ABOUT)
router.message.register(show_about, Command("about"))
router.message.register(show_contact, F.text == wb.B_CONTACT)
router.message.register(show_contact, Command("aloqa"))
router.message.register(show_pwreset, F.text == wb.B_PWRESET)
router.message.register(show_pwreset, Command("parol"))


# ====================================================================== #
#  Bekor qilish (istalgan holatda)
# ====================================================================== #
@router.message(F.text == "🚫 Bekor qilish")
@router.message(Command("cancel"))
async def do_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi. Quyidagi menyudan davom eting 👇",
                         reply_markup=kb.main_menu())


# ====================================================================== #
#  Inline navigatsiya (callback)
# ====================================================================== #
@router.callback_query(F.data == 'home')
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await _safe_edit(cb, "🏠 <b>Bosh menyu</b>\n\nQuyidagi pastki tugmalardan foydalaning 👇", [])
    await cb.answer()


@router.callback_query(F.data == 'about')
async def cb_about(cb: CallbackQuery):
    await _safe_edit(cb, wb._about(), wb._back_home_inline())
    await cb.answer()


@router.callback_query(F.data == 'contact')
async def cb_contact(cb: CallbackQuery):
    await _safe_edit(cb, wb._contact(), wb._back_home_inline())
    await cb.answer()


@router.callback_query(F.data == 'myapps')
async def cb_myapps(cb: CallbackQuery):
    text = await db.my_apps_text(cb.message.chat.id)
    await _safe_edit(cb, text, wb._back_home_inline())
    await cb.answer()


@router.callback_query(F.data.startswith('subjects'))
async def cb_subjects(cb: CallbackQuery):
    parts = cb.data.split(':')
    mode = parts[1] if len(parts) > 1 else 'browse'
    text, rows = await db.subjects_view(mode)
    await _safe_edit(cb, text, rows)
    await cb.answer()


@router.callback_query(F.data.startswith('subj:'))
async def cb_subj(cb: CallbackQuery):
    parts = cb.data.split(':')
    sid, mode = parts[1], (parts[2] if len(parts) > 2 else 'browse')
    text, rows = await db.courses_in_subject_view(sid, mode)
    await _safe_edit(cb, text, rows)
    await cb.answer()


@router.callback_query(F.data.startswith('course:'))
async def cb_course(cb: CallbackQuery):
    cid = cb.data.split(':')[1]
    text, rows = await db.course_detail(cid)
    await _safe_edit(cb, text, rows)
    await cb.answer()


@router.callback_query(F.data.startswith('reg:'))
async def cb_register(cb: CallbackQuery, state: FSMContext):
    course_id = cb.data.split(':')[1]
    course = await db.get_course_brief(course_id)
    if not course:
        await cb.answer("Guruh topilmadi.", show_alert=True)
        return
    await state.set_state(Reg.name)
    await state.update_data(course_id=course['id'], subject_id=course['subject_id'],
                            course_name=course['name'])
    await cb.message.answer(
        f"📝 <b>{course['name']}</b> guruhiga ro'yxatdan o'tish.\n\n"
        f"1/3 — Iltimos, <b>ism va familiyangizni</b> to'liq yozing:"
    )
    await cb.answer()


@router.callback_query(F.data == 'skip_age')
async def cb_skip_age(cb: CallbackQuery, state: FSMContext):
    if await state.get_state() == Reg.age.state:
        await _finish(cb.message, state, cb.message.chat.id, age=None)
    await cb.answer()


# ====================================================================== #
#  Ro'yxatdan o'tish FSM
# ====================================================================== #
@router.message(Reg.name, F.text)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Iltimos, to'liq <b>ism va familiyangizni</b> yozing:")
        return
    await state.update_data(full_name=name[:200])
    await state.set_state(Reg.phone)
    await message.answer(
        f"Rahmat, {name.split()[0]}! 🙌\n\n"
        f"2/3 — Endi <b>telefon raqamingizni</b> yuboring "
        f"(pastdagi tugma orqali yoki qo'lda, masalan +998901234567):",
        reply_markup=kb.share_phone(),
    )


@router.message(Reg.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext):
    await _save_phone(message, state, message.contact.phone_number)


@router.message(Reg.phone, F.text)
async def reg_phone_text(message: Message, state: FSMContext):
    await _save_phone(message, state, message.text.strip())


async def _save_phone(message: Message, state: FSMContext, phone: str):
    phone = (phone or "").strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 7:
        await message.answer("To'g'ri telefon raqam yuboring (masalan +998901234567):",
                             reply_markup=kb.share_phone())
        return
    await state.update_data(phone=phone)
    await state.set_state(Reg.age)
    await message.answer(
        "3/3 — O'quvchining <b>yoshini</b> raqamda yozing (masalan: 14).\n"
        "Agar ko'rsatishni xohlamasangiz — «O'tkazib yuborish».",
        reply_markup=kb.main_menu(),
    )
    await message.answer("👇", reply_markup=kb.skip_age())


@router.message(Reg.age, F.text)
async def reg_age(message: Message, state: FSMContext):
    digits = "".join(c for c in message.text if c.isdigit())
    if not digits:
        await message.answer(
            "Yoshni raqamda yozing (masalan: 14) yoki «O'tkazib yuborish» tugmasini bosing.",
            reply_markup=kb.skip_age(),
        )
        return
    await _finish(message, state, message.chat.id, age=min(int(digits), 120))


async def _finish(message: Message, state: FSMContext, chat_id, age=None):
    data = await state.get_data()
    full_name = data.get("full_name", "Noma'lum")
    phone = data.get("phone", "")
    await db.create_application(full_name, phone, age, data.get("course_id"),
                               data.get("subject_id"), chat_id)
    await state.clear()

    course_name = data.get("course_name")
    course_line = f"📚 Guruh: <b>{course_name}</b>\n" if course_name else ""
    age_line = f"🎂 Yosh: {age}\n" if age else ""
    await message.answer(
        f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
        f"{course_line}"
        f"👤 F.I.O: {full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"{age_line}\n"
        f"Markaz ma'muriyati tez orada siz bilan bog'lanadi. "
        f"Tasdiqlangach — <b>shaxsiy kabinet havolasi, login va parol</b> "
        f"aynan shu botga yuboriladi. Rahmat! 🙏",
        reply_markup=kb.main_menu(),
    )


# ====================================================================== #
#  Ro'yxatdan o'tish (inline tugmadan) va Parolni tiklash
# ====================================================================== #
@router.callback_query(F.data == 'reg_start')
async def cb_reg_start(cb: CallbackQuery, state: FSMContext):
    await _start_reg_form(cb.message, state)
    await cb.answer()


@router.callback_query(F.data == 'pwreset')
async def cb_pwreset(cb: CallbackQuery):
    text, rows = await db.pwreset_menu()
    await _safe_edit(cb, text, rows)
    await cb.answer()


@router.callback_query(F.data.startswith('pwrole:'))
async def cb_pwrole(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(':')
    role = parts[1] if len(parts) > 1 else 'student'
    await state.set_state(PwReset.login)
    await state.update_data(pwreset_role=role)
    role_label = "o'qituvchi" if role == 'teacher' else "o'quvchi"
    await cb.message.answer(
        f"🔑 <b>Parolni tiklash — {role_label}</b>\n\n"
        f"Iltimos, tizimdagi <b>loginingizni</b> (yoki ro'yxatdan o'tgan telefon "
        f"raqamingizni) yuboring:",
        reply_markup=kb.cancel_only(),
    )
    await cb.answer()


@router.message(PwReset.login, F.text)
async def pwreset_login(message: Message, state: FSMContext):
    identifier = message.text.strip()
    if len(identifier) < 3:
        await message.answer("Iltimos, to'g'ri <b>login</b> yoki <b>telefon</b> yuboring:")
        return
    data = await state.get_data()
    role = data.get('pwreset_role', 'student')
    await db.create_pwreset_request(message.chat.id, role, identifier)
    await state.clear()
    await message.answer(
        "✅ <b>Murojaatingiz yuborildi!</b>\n\n"
        "Administrator loginingizni tekshirib, yangi parol o'rnatadi. "
        "Yangi parolingiz aynan shu botga yuboriladi. 🔔\n\n"
        "Iltimos, kuting. 🙏",
        reply_markup=kb.main_menu(),
    )


# ====================================================================== #
#  Boshqa har qanday xabar — bosh menyu
# ====================================================================== #
@router.message(StateFilter(None))
async def fallback(message: Message):
    await message.answer(wb._welcome(message.from_user.first_name or ""),
                         reply_markup=kb.main_menu())
    await message.answer("Tezkor harakatlar 👇", reply_markup=kb.to_inline(wb._home_inline()))
