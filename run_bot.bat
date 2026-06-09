@echo off
REM Fan Lider Telegram bot (aiogram, polling) ishga tushirish
cd /d "%~dp0"
".venv\Scripts\python.exe" -m telegram_bot.main
pause
