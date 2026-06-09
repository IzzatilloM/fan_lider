"""Bot xabarlari (matnlar). HTML formatda."""
from .config import BRAND_NAME, CENTER_ADDRESS, CENTER_PHONE


def welcome(name=""):
    salom = f", {name}" if name else ""
    return (
        f"🎓 <b>{BRAND_NAME} o'quv markazi</b>ga xush kelibsiz{salom}!\n\n"
        f"Biz zamonaviy uslublar asosida sifatli ta'lim beramiz:\n"
        f"• 👨‍🏫 Tajribali o'qituvchilar\n"
        f"• 👥 Kichik guruhlar va individual e'tibor\n"
        f"• 📊 Davomat, baholar va to'lovlar — shaffof nazorat\n"
        f"• 📱 Har bir o'quvchiga shaxsiy onlayn kabinet\n\n"
        f"Quyidagi menyudan tanlang 👇"
    )


def about():
    return (
        f"ℹ️ <b>{BRAND_NAME} o'quv markazi haqida</b>\n\n"
        f"Bizning maqsadimiz — har bir o'quvchining bilimini real natijaga aylantirish.\n\n"
        f"✅ Zamonaviy o'quv dasturi va metodikasi\n"
        f"✅ Qulay jadval (haftada 3 kun)\n"
        f"✅ Doimiy monitoring va hisobotlar\n"
        f"✅ Ota-onalar bilan muloqot\n"
        f"✅ Shaxsiy kabinet: baholar, davomat, to'lovlar\n\n"
        f"📝 Ro'yxatdan o'tish uchun pastdagi tugmani bosing."
    )


def contact():
    return (
        f"📞 <b>{BRAND_NAME} bilan bog'lanish</b>\n\n"
        f"☎️ Telefon: {CENTER_PHONE}\n"
        f"📍 Manzil: {CENTER_ADDRESS}\n"
        f"🕘 Ish vaqti: Dushanba–Shanba, 09:00–19:00\n\n"
        f"Savolingizni shu yerga yozib qoldiring — administrator javob beradi."
    )


def ask_name():
    return "📝 <b>Ro'yxatdan o'tish</b>\n\nIltimos, <b>ism va familiyangizni</b> to'liq yozing:"


def ask_phone(first_name):
    return (
        f"Rahmat, {first_name}! 🙌\n\n"
        f"Endi <b>telefon raqamingizni</b> yuboring "
        f"(pastdagi tugma orqali yoki qo'lda, masalan +998901234567):"
    )


def application_done(full_name, phone):
    return (
        f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
        f"👤 Ism: {full_name}\n"
        f"📞 Telefon: {phone}\n\n"
        f"Markaz ma'muriyati tez orada siz bilan bog'lanadi. "
        f"Tasdiqlangach, sizga <b>shaxsiy kabinet havolasi va parol</b> aynan shu botga yuboriladi. "
        f"Rahmat! 🙏"
    )


def no_courses():
    return "Hozircha faol guruhlar yo'q. Tez orada yangilanadi. 🔄"


def courses_header():
    return "📚 <b>Faol kurslar / guruhlar:</b>\n"
