"""Inline va reply klaviaturalar (aiogram 3.x).

Inline tugmalar kontenti webhook bot (`cabinet.bot`) bilan bitta manbadan
olinadi — `to_inline()` o'sha [[{'text','callback_data'}]] tuzilmasini
aiogram InlineKeyboardMarkup ga aylantiradi.
"""
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

from cabinet.bot import (
    B_ABOUT, B_CONTACT, B_COURSES, B_MYAPPS, B_PWRESET, B_REGISTER,
)


def to_inline(rows):
    """[[{'text','callback_data'}]] → InlineKeyboardMarkup."""
    kb = []
    for row in rows or []:
        kb.append([
            InlineKeyboardButton(text=b['text'], callback_data=b['callback_data'])
            for b in row
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def main_menu():
    """Doimiy pastki menyu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B_COURSES), KeyboardButton(text=B_REGISTER)],
            [KeyboardButton(text=B_MYAPPS), KeyboardButton(text=B_ABOUT)],
            [KeyboardButton(text=B_CONTACT), KeyboardButton(text=B_PWRESET)],
        ],
        resize_keyboard=True,
    )


def cancel_only():
    """Faqat «Bekor qilish» tugmasi — forma bosqichlarida ko'rsatiladi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚫 Bekor qilish")]],
        resize_keyboard=True,
    )


def share_phone():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="🚫 Bekor qilish")],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )


def skip_age():
    return to_inline([[{'text': "⏭ O'tkazib yuborish", 'callback_data': 'skip_age'}]])


def remove():
    return ReplyKeyboardRemove()
