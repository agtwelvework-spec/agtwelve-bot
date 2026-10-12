import asyncio
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import repository
from keyboards.reminders_kb import reminders_kb, reminders_text, has_any
from keyboards.main_menu import main_menu

router = Router()


# ═══════════════════════════════════════
#  РУЧНОЙ ПРОСМОТР
# ═══════════════════════════════════════

@router.message(Command("reminders"))
@router.message(F.text == "🔔 Reminders")
async def reminders(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    waiting_me, waiting_him, silent = repository.get_due_contacts(user_id)

    if not has_any(waiting_me, waiting_him, silent):
        await message.answer("😎 Братан, все под контролем. Никому писать не надо.")
        return

    await message.answer(
        reminders_text(waiting_me, waiting_him, silent),
        reply_markup=reminders_kb(waiting_me, waiting_him, silent)
    )


@router.callback_query(F.data == "reminders_done")
async def reminders_done(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    repository.snooze_all(user_id, days=7)
    await callback.message.edit_text("✅ Красавчик. Все отложены на 7 дней.")
    await callback.answer()


@router.callback_query(F.data == "reminders_snooze")
async def reminders_snooze(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    repository.snooze_all(user_id, days=3)
    await callback.message.edit_text("⏰ Все напоминания отложены на 3 дня.")
    await callback.answer()


# ═══════════════════════════════════════
#  КНОПКИ СТАТУСА
# ═══════════════════════════════════════

async def _refresh_card(callback: types.CallbackQuery, user_id: int, contact_id: int):
    from handlers.contacts import contact_text
    from keyboards.contact_kb import contact_card_kb
    c = repository.get_contact_by_id(user_id, contact_id)
    if c:
        await callback.message.edit_text(contact_text(c), reply_markup=contact_card_kb(contact_id))


@router.callback_query(F.data.startswith("wrote:"))
async def mark_wrote(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    repository.set_status(user_id, cid, "me", "wrote")
    repository.add_history(user_id, cid, "написал")
    await callback.answer("💬 Отметил. Напомню через 3 дня.")
    await _refresh_card(callback, user_id, cid)


@router.callback_query(F.data.startswith("beat:"))
async def mark_beat(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    repository.set_status(user_id, cid, "me", "sent_beat")
    repository.add_history(user_id, cid, "отправил бит")
    await callback.answer("📤 Отметил. Напомню через 3 дня.")
    await _refresh_card(callback, user_id, cid)


@router.callback_query(F.data.startswith("replied:"))
async def mark_replied(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    repository.set_status(user_id, cid, "him", "replied")
    repository.add_history(user_id, cid, "ответил")
    await callback.answer("✅ Отметил. Теперь твой ход.")
    await _refresh_card(callback, user_id, cid)


@router.callback_query(F.data.startswith("promised:"))
async def mark_promised(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    repository.set_status(user_id, cid, "him", "promised")
    repository.add_history(user_id, cid, "обещал написать")
    await callback.answer("🤝 Отметил. Не дави.")
    await _refresh_card(callback, user_id, cid)


@router.callback_query(F.data.startswith("snooze:"))
async def snooze_one(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    repository.set_status(user_id, cid, "me")
    await callback.answer("⏰ Отложил на 3 дня.")
    await _refresh_card(callback, user_id, cid)


# ═══════════════════════════════════════
#  АВТОНАПОМИНАНИЯ (ОТКЛЮЧЕНЫ — мультиюзер)
# ═══════════════════════════════════════
#
# В мультипользовательском режиме — scheduler писал бы ВСЕМ юзерам.
# Это надо переделать: для каждого юзера — свой таймер.
# Пока откладываем — вернёмся, когда бот будет на сервере.