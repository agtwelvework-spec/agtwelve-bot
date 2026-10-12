from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Find"), KeyboardButton(text="📋 See all")],
            [KeyboardButton(text="➕ Add contact"), KeyboardButton(text="✏️ Edit contact")],
            [KeyboardButton(text="🗑 Delete contact"), KeyboardButton(text="🔔 Reminders")],
            [KeyboardButton(text="📋 Шаблоны"), KeyboardButton(text="✉️ Mailings")],
        ],
        resize_keyboard=True
    )
    return kb