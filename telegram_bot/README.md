# Fan Lider — Telegram bot (aiogram 3.x)

To'liq mustaqil bot. Django ORM bilan ishlaydi (bir xil baza: kurslar, arizalar, o'quvchilar).

## Imkoniyatlari
- `/start` — markaz haqida professional taqdimot + menyu
- 📚 **Kurslar** — faol guruhlar (o'qituvchi, jadval, vaqt, narx, level)
- 📝 **Ro'yxatdan o'tish** — ism + telefon (FSM bosqichli) → ariza CRM ga tushadi
  (admin "Onlayn arizalar"da ko'radi → tasdiqlaydi → o'quvchiga aylantiradi)
- ℹ️ **Markaz haqida**, 📞 **Aloqa**
- Admin login yaratganda kabinet havolasi + parol shu botga avtomatik yuboriladi
  (Django tomonida `cabinet/telegram.py` orqali).

## Sozlash
`.env` faylida:
```
TELEGRAM_BOT_TOKEN=8479550724:AAGV...   # @BotFather dan
SITE_URL=https://<siz>.pythonanywhere.com   # kabinet havolasi uchun
CENTER_PHONE=+998 90 123 45 67
CENTER_ADDRESS=Toshkent sh., ...
```

## Ishga tushirish (polling)
Loyiha ildizidan (`Fan_lider_CRM/`):
```powershell
.venv\Scripts\python -m telegram_bot.main
```
yoki Windows'da `run_bot.bat` faylini ikki marta bosing.

> Polling rejimi doimiy yoqilgan kompyuter/VPS talab qiladi.
> PythonAnywhere **bepul** akkauntda polling ishlamaydi — u yerda
> webhook ishlatiladi (`python manage.py set_telegram_webhook`).

## Tuzilma
```
telegram_bot/
  config.py     — Django setup + token
  texts.py      — barcha xabar matnlari
  keyboards.py  — inline / reply tugmalar
  db.py         — Django ORM (async wrapperlar)
  handlers.py   — handlerlar + FSM (Reg.name, Reg.phone)
  main.py       — kirish nuqtasi (polling)
```
