from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime


def reminders_kb(waiting_me, waiting_him, silent):
    kb = InlineKeyboardBuilder()
    counter = 1

    for group in (waiting_me, waiting_him, silent):
        for c in group:
            kb.button(text=str(counter), callback_data=f"contact:{c['id']}")
            counter += 1

    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="✅ Всё сделал", callback_data="reminders_done"))
    kb.row(InlineKeyboardButton(text="⏰ Отложить всех на 3 дня", callback_data="reminders_snooze"))
    return kb.as_markup()


def reminders_text(waiting_me, waiting_him, silent):
    text = "🔔 Братан, вот расклад:\n\n"
    counter = 1

    groups = [
        ("🔥 ЖДЁШЬ ТЫ", waiting_me),
        ("⏳ ЖДУТ ТЕБЯ", waiting_him),
        ("💤 ЗАМОЛЧАЛИ", silent),
    ]

    for title, group in groups:
        if not group:
            continue
        text += f"{title} ({len(group)}):\n"
        for c in group:
            days = (datetime.now() - datetime.fromisoformat(c["last_contact_at"])).days
            text += f"{counter}. {c['name']} — {days} дн.\n"
            counter += 1
        text += "\n"

    text += "Нажми цифру, чтобы открыть контакт."
    return text


def has_any(waiting_me, waiting_him, silent):
    return bool(waiting_me or waiting_him or silent)