"""Fan Lider Telegram bot — aiogram 3.x (polling).

Ishga tushirish (loyiha ildizidan):
    .venv\\Scripts\\python -m telegram_bot.main
yoki:
    python -m telegram_bot.main

Eslatma: bot Django ORM bilan ishlaydi (bir xil baza).
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from .config import BOT_TOKEN
from .handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fanlider_bot")

COMMANDS = [
    BotCommand(command="start", description="Boshlash / asosiy menyu"),
    BotCommand(command="kurslar", description="Faol kurslar va guruhlar"),
    BotCommand(command="royxat", description="Guruhga ro'yxatdan o'tish"),
    BotCommand(command="arizalarim", description="Mening arizalarim holati"),
    BotCommand(command="aloqa", description="Biz bilan bog'lanish"),
]


async def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN topilmadi. .env fayliga tokenni qo'shing."
        )

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Polling uchun webhook o'chiriladi (agar oldin o'rnatilgan bo'lsa)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(COMMANDS)

    me = await bot.get_me()
    logger.info("Bot ishga tushdi: @%s (%s)", me.username, me.first_name)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
