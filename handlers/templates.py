from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from database import repository
from keyboards.main_menu import main_menu

router = Router()


class NewTemplate(StatesGroup):
    name = State()
    subject = State()
    body = State()


class EditTemplate(StatesGroup):
    name = State()
    subject = State()
    body = State()


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def inline(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])


def templates_kb(templates):
    rows = [[(f"📋 {t['name']}", f"tpl_view:{t['id']}")] for t in templates]
    rows.append([("➕ Создать шаблон", "tpl_new")])
    rows.append([("❌ Закрыть", "tpl_close")])
    return inline(rows)


def template_view_kb(template_id):
    return inline([
        [("✏️ Редактировать", f"tpl_edit:{template_id}")],
        [("🗑 Удалить", f"tpl_delete:{template_id}")],
        [("⬅️ Назад", "tpl_list")],
    ])


# ═══════════════════════════════════════
#  СПИСОК
# ═══════════════════════════════════════

@router.message(Command("templates"))
@router.message(F.text == "📋 Шаблоны")
async def templates_list(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    templates = repository.get_all_templates(user_id)

    if not templates:
        await message.answer(
            "📋 Шаблонов пока нет.\n\nСоздай первый — он пригодится при отправке писем.",
            reply_markup=inline([[("➕ Создать шаблон", "tpl_new")]])
        )
        return

    await message.answer(
        f"📋 Твои шаблоны ({len(templates)}):",
        reply_markup=templates_kb(templates)
    )


@router.callback_query(F.data == "tpl_list")
async def tpl_list(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    templates = repository.get_all_templates(user_id)
    if not templates:
        await callback.message.edit_text(
            "📋 Шаблонов пока нет.",
            reply_markup=inline([[("➕ Создать шаблон", "tpl_new")]])
        )
        return await callback.answer()

    await callback.message.edit_text(
        f"📋 Твои шаблоны ({len(templates)}):",
        reply_markup=templates_kb(templates)
    )
    await callback.answer()


@router.callback_query(F.data == "tpl_close")
async def tpl_close(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ═══════════════════════════════════════
#  ПРОСМОТР
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("tpl_view:"))
async def tpl_view(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tid = int(callback.data.split(":")[1])
    t = repository.get_template_by_id(user_id, tid)

    if not t:
        return await callback.answer("Не найден", show_alert=True)

    await callback.message.edit_text(
        f"📋 {t['name']}\n\nТема: {t['subject']}\n\n{t['body']}\n\n"
        f"Переменные: {{name}}, {{genre}}, {{instagram}}",
        reply_markup=template_view_kb(tid)
    )
    await callback.answer()


# ═══════════════════════════════════════
#  СОЗДАНИЕ
# ═══════════════════════════════════════

@router.callback_query(F.data == "tpl_new")
async def tpl_new(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "📋 Как назовём шаблон?\n\nНапример: «Первое письмо», «Follow-up»",
        reply_markup=cancel_kb()
    )
    await state.set_state(NewTemplate.name)
    await callback.answer()


@router.message(NewTemplate.name)
async def tpl_new_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())
    await state.update_data(name=message.text.strip())
    await message.answer("Тема письма?", reply_markup=cancel_kb())
    await state.set_state(NewTemplate.subject)


@router.message(NewTemplate.subject)
async def tpl_new_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())
    await state.update_data(subject=message.text.strip())
    await message.answer(
        "Текст письма?\n\nМожешь использовать переменные:\n"
        "{name} — имя контакта\n{genre} — жанр\n{instagram} — ник в инсте",
        reply_markup=cancel_kb()
    )
    await state.set_state(NewTemplate.body)


@router.message(NewTemplate.body)
async def tpl_new_body(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())

    user_id = message.from_user.id
    data = await state.get_data()
    await state.clear()

    repository.add_template(user_id, data["name"], data["subject"], message.text.strip())
    await message.answer(f"✅ Шаблон «{data['name']}» создан!", reply_markup=main_menu())


# ═══════════════════════════════════════
#  РЕДАКТИРОВАНИЕ
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("tpl_edit:"))
async def tpl_edit(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    tid = int(callback.data.split(":")[1])
    t = repository.get_template_by_id(user_id, tid)
    if not t:
        return await callback.answer("Не найден", show_alert=True)

    await state.update_data(template_id=tid)
    await callback.message.answer(
        f"✏️ Введи новое название.\n\nСейчас: «{t['name']}»",
        reply_markup=cancel_kb()
    )
    await state.set_state(EditTemplate.name)
    await callback.answer()


@router.message(EditTemplate.name)
async def tpl_edit_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())
    await state.update_data(name=message.text.strip())
    await message.answer("Новая тема?", reply_markup=cancel_kb())
    await state.set_state(EditTemplate.subject)


@router.message(EditTemplate.subject)
async def tpl_edit_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())
    await state.update_data(subject=message.text.strip())
    await message.answer("Новый текст?", reply_markup=cancel_kb())
    await state.set_state(EditTemplate.body)


@router.message(EditTemplate.body)
async def tpl_edit_body(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await message.answer("Отменено.", reply_markup=main_menu())

    user_id = message.from_user.id
    data = await state.get_data()
    await state.clear()

    repository.update_template(user_id, data["template_id"], data["name"], data["subject"], message.text.strip())
    await message.answer("✅ Шаблон обновлён!", reply_markup=main_menu())


# ═══════════════════════════════════════
#  УДАЛЕНИЕ
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("tpl_delete:"))
async def tpl_delete_confirm(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tid = int(callback.data.split(":")[1])
    t = repository.get_template_by_id(user_id, tid)
    if not t:
        return await callback.answer("Не найден", show_alert=True)

    await callback.message.edit_text(
        f"⚠️ Удалить шаблон «{t['name']}»?",
        reply_markup=inline([
            [("🗑 Да, удалить", f"tpl_confirm_delete:{tid}")],
            [("⬅️ Отмена", f"tpl_view:{tid}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tpl_confirm_delete:"))
async def tpl_delete(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tid = int(callback.data.split(":")[1])
    repository.delete_template(user_id, tid)
    await callback.message.edit_text("🗑 Шаблон удалён.")
    await callback.answer()

    templates = repository.get_all_templates(user_id)
    if templates:
        await callback.message.answer(f"📋 Твои шаблоны ({len(templates)}):", reply_markup=templates_kb(templates))
    else:
        await callback.message.answer("📋 Шаблонов больше нет.")