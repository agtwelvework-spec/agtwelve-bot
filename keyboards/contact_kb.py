from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def search_results_kb(contacts):
    kb = InlineKeyboardBuilder()
    for c in contacts:
        label = c["name"]
        if c["genre"]:
            label += f" — {c['genre']}"
        kb.button(text=label, callback_data=f"contact:{c['id']}")
    kb.button(text="❌ Закрыть", callback_data="close")
    kb.adjust(1)
    return kb.as_markup()


def contact_card_kb(contact_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✉️ Написать письмо", callback_data=f"mail:{contact_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{contact_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{contact_id}"),
        ],
        [
            InlineKeyboardButton(text="💬 Написал", callback_data=f"wrote:{contact_id}"),
            InlineKeyboardButton(text="📤 Отправил бит", callback_data=f"beat:{contact_id}"),
        ],
        [
            InlineKeyboardButton(text="📜 История", callback_data=f"history:{contact_id}"),
            InlineKeyboardButton(text="🔔 Отложить", callback_data=f"snooze:{contact_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_search"),
        ],
    ])
    return kb