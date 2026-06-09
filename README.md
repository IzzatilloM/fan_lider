# Fan Lider CRM — O'quv Markazi Boshqaruv Tizimi

Professional o'quv markazi CRM tizimi. Uchta asosiy modul atrofida qurilgan:

| Modul | Tavsif |
|-------|--------|
| 📝 **Onlayn ro'yxatdan o'tish** | Ommaviy ariza shakli + lead funnel (yangi → bog'lanildi → sinov → ro'yxatga olindi). Arizani bitta tugma bilan o'quvchiga aylantirish. |
| 💳 **To'lovlarni boshqarish** | Hisob-fakturalarni avtomatik oylik generatsiya qilish, kassa to'lovlari (naqd/karta/Click/Payme), avtomatik balans va qarzdorlik nazorati. |
| 📈 **O'quv jarayonini monitoring** | Guruh davomati (jurnal + matritsa), baholar jurnali va reyting, dars mavzulari jurnali, o'quvchi bo'yicha to'liq hisobot. |

Asosiy rang: **`#D4640F`** (barcha sahifalarda). Tizimga kirish: **admin/direktor Telegram bot (chat ID + tasdiqlash kodi)** orqali ro'yxatdan o'tadi, so'ng **login + parol** bilan kiradi; **o'qituvchi/o'quvchini admin yaratadi** (login + parol beradi). Qo'shimcha modul: **xodimlar oyligini suniy intellekt (Claude) bilan hisoblash**.

---

## 🧩 Texnologiyalar
- **Django 6.0** (allauth/Google'siz — Telegram kodi bilan ro'yxatdan o'tish + parolli kirish)
- **Bootstrap 5** (kirish/ro'yxat sahifalari) + Vanilla CSS dizayn tizimi (ichki panel) + Chart.js
- **WhiteNoise** (statik fayllar)
- **Anthropic Claude** SDK (oylik AI tahlili, ixtiyoriy)
- SQLite (default) yoki PostgreSQL

## 📂 Ilovalar
```
accounts     — Telegram-kod ro'yxatdan o'tish + login/parol auth, rollar (admin/direktor/o'qituvchi/o'quvchi), sozlamalar
courses      — Yo'nalishlar (Subject) va guruhlar (Course)
students     — O'quvchilar
instructors  — O'qituvchilar va xodimlar/rollar boshqaruvi
enrollments  — Onlayn arizalar + guruhga yozilishlar
payments     — Hisob-fakturalar va to'lovlar
monitoring   — Davomat, baholar, dars jurnali
salaries     — Xodimlar oyligini AI (Claude) bilan hisoblash + payslip
dashboard    — Analitika boshqaruv paneli
```

---

## 🚀 Lokal ishga tushirish (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # yoki mavjud .env ni tahrirlang
python manage.py migrate
python manage.py seed_demo          # (ixtiyoriy) namunaviy ma'lumotlar
python manage.py runserver
```

`http://127.0.0.1:8000/` ochiladi → **Kirish / Ro'yxatdan o'tish**.

> **Telegram kerak:** kod botga yuborilgani uchun `.env` da `TELEGRAM_BOT_TOKEN` to'g'ri bo'lishi va foydalanuvchi botni `/start` bilan bir marta ishga tushirgan bo'lishi shart. Zaxira: `python manage.py createsuperuser` bilan yaratilgan superuser har doim login+parol bilan `/admin/` va saytga kira oladi.

---

## 🔐 Kirish va ro'yxatdan o'tish (Telegram kodi + parol)

**Admin / Direktor — ro'yxatdan o'tish:**
1. Telegram botni oching, **«🆔 ID raqamim»** tugmasini bosib chat ID raqamingizni oling.
2. Saytda **Ro'yxatdan o'tish** → lavozim, ism, **login**, **Telegram ID** va **parol** kiritiladi.
3. **«Botga kod yuborish»** bosiladi — 6 xonali kod aynan shu botga keladi.
4. Kod tasdiqlangach hisob yaratiladi. Keyingi kirishlar **login + parol** orqali.
5. Parolni unutsa — **Parolni tiklash** → Telegram ID → botga kod → yangi parol.

**O'qituvchi / O'quvchi:** ro'yxatdan o'tmaydi — ularni **admin yaratadi** (login + parol beradi). Parolni unutsa, botdagi **«🔑 Parolni tiklash»** orqali adminga murojaat qiladi.

### Cheklovlar
`.env` orqali sozlanadi (slot tugasa yangi ro'yxatdan o'tish ko'rinmaydi):
```
MAX_ADMINS=2
MAX_DIRECTORS=1
```
Tizim butunlay bo'sh bo'lsa, birinchi ro'yxatdan o'tgan foydalanuvchi avto-admin bo'ladi.

### ⚙️ Sozlamalar (admin)
`/accounts/settings/` — admin **o'z parolini o'zgartiradi**, **markaz ma'lumotlarini** (nom, telefon, manzil, bot, logo) tahrirlaydi va **barcha o'quvchi/o'qituvchilarning login va parollarini** ko'radi, tahrirlaydi yoki o'chiradi.

---

## 💰 Xodimlar oyligi (AI bilan)

`/salaries/` bo'limi xodimlar oyligini avtomatik hisoblaydi:
- **Formula + KPI dvigateli**: belgilangan oylik / soatbay / o'quvchi soniga qarab + KPI bonusi (davomat va o'zlashtirish) − jarimalar.
- O'qituvchilar uchun metrikalar (darslar, davomat, o'zlashtirish) **monitoring ma'lumotlaridan avtomatik** yig'iladi.
- **Suniy intellekt tahlili**: har bir xodim oyligiga izoh, tavsiya va baho (A/B/C/D).
  - `.env` da `ANTHROPIC_API_KEY` bo'lsa — haqiqiy **Claude** tahlili.
  - Kalitsiz — **offline (mahalliy) rejim** ham to'liq ishlaydi.
- Har bir xodim uchun chop etiladigan **payslip** (oylik hisob-varaqasi).

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

---

## ☁️ PythonAnywhere'ga joylash (to'liq)

### 1. Kodni yuklash
- Faylllarni yuklang (Git yoki ZIP) → `/home/<foydalanuvchi>/Fan_lider_CRM/`.

### 2. Virtual muhit
PythonAnywhere **Bash console**:
```bash
cd ~/Fan_lider_CRM
python3.13 -m venv .venv      # mavjud Python 3.13 versiyasini ishlating
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. `.env` faylini sozlang
`/home/<foydalanuvchi>/Fan_lider_CRM/.env`:
```
DEBUG=False
SECRET_KEY=<uzun-tasodifiy-maxfiy-kalit>
ALLOWED_HOSTS=<foydalanuvchi>.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://<foydalanuvchi>.pythonanywhere.com
DB_ENGINE=sqlite
BRAND_NAME=Fan Lider
MAX_ADMINS=2
MAX_DIRECTORS=1
TELEGRAM_BOT_TOKEN=<@BotFather token>
TELEGRAM_WEBHOOK_SECRET=<tasodifiy-maxfiy-satr>
TELEGRAM_BOT_USERNAME=<bot_username>
SITE_URL=https://<foydalanuvchi>.pythonanywhere.com
ANTHROPIC_API_KEY=
```

### 4. Ma'lumotlar bazasi va statik fayllar
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo     # (ixtiyoriy)
```

### 5. Web ilovani yaratish
- **Web** tab → **Add a new web app** → **Manual configuration** → **Python 3.13**.
- **Virtualenv**: `/home/<foydalanuvchi>/Fan_lider_CRM/.venv`
- **WSGI configuration file** (link orqali oching) → ichidagini o'chirib, `wsgi_pythonanywhere.py` faylidagi kodni joylashtiring (`<YOURUSERNAME>` ni almashtiring).

### 6. Statik fayllar mapping (Web tab → Static files)
| URL | Directory |
|-----|-----------|
| `/static/` | `/home/<foydalanuvchi>/Fan_lider_CRM/staticfiles` |
| `/media/`  | `/home/<foydalanuvchi>/Fan_lider_CRM/media` |

### 7. Saytni qayta yuklang (**Reload** tugmasi)
- `https://<foydalanuvchi>.pythonanywhere.com/` ochiladi.
- Birinchi **Ro'yxatdan o'tish** (Telegram ID + kod) → birinchi foydalanuvchi avto-admin bo'ladi. Zaxira sifatida `python manage.py createsuperuser` ham yarating.

> **Muhim:** Telegram kodi yuborilishi uchun `.env` da `TELEGRAM_BOT_TOKEN` to'g'ri bo'lishi va webhook sozlangan bo'lishi kerak (`python manage.py set_telegram_webhook`). Foydalanuvchi botni bir marta `/start` qilgan bo'lishi shart.

---

## 👥 Rollar
| Rol | Huquqlar |
|-----|----------|
| **Administrator** | Hammasi: foydalanuvchilar, sozlamalar, barcha panellar |
| **Direktor** | Monitoring: to'lovlar, o'quv jarayoni, davomat, guruhlar, o'qituvchilar |
| **O'qituvchi** | O'z guruhlari: davomat, baholar, oylik (ko'rish) |
| **O'quvchi** | Shaxsiy kabinet: kurslar, baholar, davomat, to'lovlar |

Admin/direktor **o'zi** ro'yxatdan o'tadi (Telegram kodi). O'qituvchi/o'quvchini **admin yaratadi** — `O'qituvchi` roli berilsa, avtomatik o'qituvchi profili yaratiladi.

## 🌐 Ommaviy ariza sahifasi
`/registration/apply/` — tizimga kirmasdan ochiladi. Markaz veb-saytiga yoki Instagram bio'ga shu havolani qo'ying.
