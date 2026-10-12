import os
import aiohttp
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
from keyboards.contact_kb import search_results_kb, contact_card_kb
from services import mailer
from config import MAX_ATTACHMENT_MB

router = Router()
TEMP_DIR = "data/temp"
os.makedirs(TEMP_DIR, exist_ok=True)


# ═══════════════════════════════════════
#  ХЕЛПЕРЫ
# ═══════════════════════════════════════

async def download_file_stream(telegram_file_path, save_path):
    from config import TOKEN
    url = f"https://api.telegram.org/file/bot{TOKEN}/{telegram_file_path}"
    timeout = aiohttp.ClientTimeout(total=600, connect=30, sock_read=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Telegram вернул {resp.status}")
            with open(save_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    f.write(chunk)


def apply_template(text, contact):
    if not text:
        return ""
    return (text
        .replace("{name}", contact["name"] or "")
        .replace("{genre}", contact["genre"] or "")
        .replace("{instagram}", contact["instagram"] or "")
    )


def kb(buttons, resize=True):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=b) for b in row] for row in buttons],
        resize_keyboard=True
    )


def cancel_kb():
    return kb([["❌ Отмена"]])


def skip_cancel_kb():
    return kb([["⏭ Пропустить", "❌ Отмена"]])


def inline(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])


def contact_text(c):
    waiting = c["waiting_on"] if "waiting_on" in c.keys() else "nobody"
    status = ""
    if waiting == "me":
        status = "\n⏳ Ждёшь ответа"
    elif waiting == "him":
        status = "\n⏳ Ждут тебя"

    return (
        f"👤 {c['name']}\n"
        f"📧 {c['email'] or '—'}\n"
        f"📷 {c['instagram'] or '—'}\n"
        f"📍 {c['source'] or '—'}\n"
        f"🎵 {c['genre'] or '—'}\n"
        f"📅 Последний контакт: {c['last_contact_at']}\n"
        f"📝 {c['notes'] or '—'}\n"
        f"ID: {c['id']}{status}"
    )


async def show_card(message_or_cb, user_id, contact_id, edit=False):
    c = repository.get_contact_by_id(user_id, contact_id)
    if not c:
        return
    text = contact_text(c)
    markup = contact_card_kb(contact_id)
    if edit and hasattr(message_or_cb, "edit_text"):
        await message_or_cb.edit_text(text, reply_markup=markup)
    else:
        await message_or_cb.answer(text, reply_markup=markup)


# ═══════════════════════════════════════
#  СОСТОЯНИЯ
# ═══════════════════════════════════════

class AddContact(StatesGroup):
    name = State()
    email = State()
    instagram = State()
    source = State()
    genre = State()
    notes = State()


class Search(StatesGroup):
    query = State()


class EditContact(StatesGroup):
    choosing_field = State()
    entering_value = State()


class MenuSearch(StatesGroup):
    edit = State()
    delete = State()


class Mail(StatesGroup):
    choose_template = State()
    subject = State()
    body = State()
    attach = State()
    confirm = State()


FIELD_LABELS = {
    "name": "👤 Имя",
    "email": "📧 Почта",
    "instagram": "📷 Инста",
    "source": "📍 Источник",
    "genre": "🎵 Жанр",
    "notes": "📝 Заметка",
}


def edit_fields_kb(contact_id):
    rows = [[(label, f"editfield:{contact_id}:{f}")] for f, label in FIELD_LABELS.items()]
    rows.append([("⬅️ Отмена", f"contact:{contact_id}")])
    return inline(rows)


# ═══════════════════════════════════════
#  ADD CONTACT
# ═══════════════════════════════════════

ADD_STEPS = [
    ("name",      "Как зовут контакт? (имя или ник)", False),
    ("email",     "Почта?",                            True),
    ("instagram", "Ник в инсте?",                      True),
    ("source",    "Источник?",                         True),
    ("genre",     "Жанр?",                             True),
    ("notes",     "Заметка?",                          True),
]


@router.message(Command("add"))
@router.message(F.text == "➕ Add contact")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    field, question, optional = ADD_STEPS[0]
    markup = skip_cancel_kb() if optional else ReplyKeyboardRemove()
    await message.answer(question, reply_markup=markup)
    await state.set_state(getattr(AddContact, field))


async def _add_step(message, state, next_index):
    if next_index >= len(ADD_STEPS):
        data = await state.get_data()
        await state.clear()
        user_id = message.from_user.id
        cid = repository.add_contact(
            user_id=user_id,
            name=data["name"],
            email=data.get("email"),
            instagram=data.get("instagram"),
            source=data.get("source"),
            genre=data.get("genre"),
            notes=data.get("notes"),
        )
        await message.answer("✅ Контакт добавлен!", reply_markup=main_menu())
        await show_card(message, user_id, cid)
        return

    field, question, optional = ADD_STEPS[next_index]
    markup = skip_cancel_kb() if optional else ReplyKeyboardRemove()
    await message.answer(question, reply_markup=markup)
    await state.set_state(getattr(AddContact, field))


@router.message(AddContact.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await _add_step(message, state, 1)


@router.message(AddContact.email)
async def add_email(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(email=None if message.text == "⏭ Пропустить" else message.text.strip())
    await _add_step(message, state, 2)


@router.message(AddContact.instagram)
async def add_instagram(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(instagram=None if message.text == "⏭ Пропустить" else message.text.strip())
    await _add_step(message, state, 3)


@router.message(AddContact.source)
async def add_source(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(source=None if message.text == "⏭ Пропустить" else message.text.strip())
    await _add_step(message, state, 4)


@router.message(AddContact.genre)
async def add_genre(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(genre=None if message.text == "⏭ Пропустить" else message.text.strip())
    await _add_step(message, state, 5)


@router.message(AddContact.notes)
async def add_notes(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(notes=None if message.text == "⏭ Пропустить" else message.text.strip())
    await _add_step(message, state, 6)


async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


# ═══════════════════════════════════════
#  SEE ALL / FIND
# ═══════════════════════════════════════

@router.message(Command("list"))
@router.message(F.text == "📋 See all")
async def see_all(message: types.Message):
    user_id = message.from_user.id
    contacts = repository.get_all_contacts(user_id)
    if not contacts:
        await message.answer("Пока никого нет. Добавь через ➕ Add contact.")
        return
    await message.answer(
        f"📋 Все контакты ({len(contacts)}). Нажми, чтобы открыть:",
        reply_markup=search_results_kb(contacts[:30])
    )


@router.message(Command("find"))
@router.message(F.text == "🔍 Find")
async def find_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔍 Введи что угодно: имя, почту, инсту, жанр, источник, заметку.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Search.query)


@router.message(Search.query)
async def find_query(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    query = message.text.strip()
    await state.clear()
    results = repository.search_contacts(user_id, query)

    if not results:
        await message.answer(f"❌ По запросу «{query}» ничего не найдено.", reply_markup=main_menu())
        return

    await message.answer(
        f"🔍 Нашёл {len(results)} по запросу «{query}»:",
        reply_markup=search_results_kb(results)
    )
    await message.answer("Меню:", reply_markup=main_menu())


# ═══════════════════════════════════════
#  КАРТОЧКА
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("contact:"))
async def show_contact_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    if not repository.get_contact_by_id(user_id, cid):
        return await callback.answer("Не найден", show_alert=True)
    await show_card(callback.message, user_id, cid, edit=True)
    await callback.answer()


@router.callback_query(F.data.in_(["close", "back_to_search"]))
async def close_cb(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ═══════════════════════════════════════
#  РЕДАКТИРОВАНИЕ
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("edit:"))
async def edit_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    c = repository.get_contact_by_id(user_id, cid)
    if not c:
        return await callback.answer("Не найден", show_alert=True)

    await state.update_data(contact_id=cid)
    await callback.message.edit_text(f"✏️ Что меняем в «{c['name']}»?", reply_markup=edit_fields_kb(cid))
    await state.set_state(EditContact.choosing_field)
    await callback.answer()


@router.callback_query(EditContact.choosing_field, F.data.startswith("editfield:"))
async def edit_field_chosen(callback: types.CallbackQuery, state: FSMContext):
    _, cid, field = callback.data.split(":")
    await state.update_data(field=field)
    await callback.message.edit_text(
        f"{FIELD_LABELS[field]} — введи новое значение:\n\n(или `-` чтобы очистить)",
        parse_mode="Markdown"
    )
    await state.set_state(EditContact.entering_value)
    await callback.answer()


@router.message(EditContact.entering_value)
async def edit_value_entered(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    cid, field = data["contact_id"], data["field"]
    value = message.text.strip()
    if value == "-":
        value = None

    repository.update_contact_field(user_id, cid, field, value)
    await state.clear()

    await message.answer("✅ Обновлено!", reply_markup=main_menu())
    await show_card(message, user_id, cid)


# ═══════════════════════════════════════
#  УДАЛЕНИЕ
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("delete:"))
async def delete_confirm(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    c = repository.get_contact_by_id(user_id, cid)
    if not c:
        return await callback.answer("Не найден", show_alert=True)

    await callback.message.edit_text(
        f"⚠️ Удалить «{c['name']}»?\n\nВся история тоже удалится.",
        reply_markup=inline([
            [("🗑 Да, удалить", f"confirmdelete:{cid}")],
            [("⬅️ Отмена", f"contact:{cid}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirmdelete:"))
async def delete_confirmed(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    c = repository.get_contact_by_id(user_id, cid)
    name = c["name"] if c else "контакт"
    repository.delete_contact(user_id, cid)
    await callback.message.edit_text(f"🗑 «{name}» удалён.")
    await callback.message.answer("Меню:", reply_markup=main_menu())
    await callback.answer("Удалено")


# ═══════════════════════════════════════
#  EDIT / DELETE ЧЕРЕЗ МЕНЮ
# ═══════════════════════════════════════

@router.message(F.text == "✏️ Edit contact")
async def edit_from_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔍 Кого редактируем? Введи что угодно.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(MenuSearch.edit)


@router.message(F.text == "🗑 Delete contact")
async def delete_from_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔍 Кого удаляем? Введи что угодно.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(MenuSearch.delete)


@router.message(MenuSearch.edit)
async def edit_search(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    results = repository.search_contacts(user_id, message.text.strip())
    await state.clear()
    if not results:
        return await message.answer("❌ Никого не нашёл.", reply_markup=main_menu())
    await message.answer("✏️ Выбери:", reply_markup=search_results_kb(results))
    await message.answer("Меню:", reply_markup=main_menu())


@router.message(MenuSearch.delete)
async def delete_search(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    results = repository.search_contacts(user_id, message.text.strip())
    await state.clear()
    if not results:
        return await message.answer("❌ Никого не нашёл.", reply_markup=main_menu())
    await message.answer("🗑 Выбери:", reply_markup=search_results_kb(results))
    await message.answer("Меню:", reply_markup=main_menu())


# ═══════════════════════════════════════
#  ✉️ ПИСЬМО
# ═══════════════════════════════════════

def mail_templates_kb(user_id):
    templates = repository.get_all_templates(user_id)
    rows = [[(f"📋 {t['name']}", f"mail_tpl:{t['id']}")] for t in templates]
    rows.append([("✏️ Написать с нуля", "mail_manual")])
    rows.append([("❌ Отмена", "mail_cancel_start")])
    return inline(rows)


@router.callback_query(F.data.startswith("mail:"))
async def mail_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    c = repository.get_contact_by_id(user_id, cid)

    if not c:
        return await callback.answer("Не найден", show_alert=True)
    if not c["email"]:
        return await callback.answer("У контакта нет почты", show_alert=True)

    await state.update_data(contact_id=cid)

    templates = repository.get_all_templates(user_id)
    if templates:
        await state.set_state(Mail.choose_template)
        await callback.message.answer(
            f"✉️ Пишем письмо для «{c['name']}» ({c['email']})\n\n"
            f"Использовать шаблон или написать с нуля?",
            reply_markup=mail_templates_kb(user_id)
        )
    else:
        await state.set_state(Mail.subject)
        await callback.message.answer(
            f"✉️ Пишем письмо для «{c['name']}» ({c['email']})\n\nТема письма?",
            reply_markup=cancel_kb()
        )
    await callback.answer()


@router.callback_query(Mail.choose_template, F.data.startswith("mail_tpl:"))
async def mail_use_template(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    tid = int(callback.data.split(":")[1])
    t = repository.get_template_by_id(user_id, tid)
    if not t:
        return await callback.answer("Шаблон не найден", show_alert=True)

    data = await state.get_data()
    c = repository.get_contact_by_id(user_id, data["contact_id"])

    subject = apply_template(t["subject"], c)
    body = apply_template(t["body"], c)

    await state.update_data(subject=subject, body=body, attachments=[])

    await callback.message.edit_text(
        f"📋 Шаблон «{t['name']}»\n\n"
        f"Кому: {c['name']} <{c['email']}>\n"
        f"Тема: {subject}\n\n{body}\n\n"
        f"Что делаем?",
        reply_markup=inline([
            [("✏️ Изменить тему", "mail_edit_subject")],
            [("✏️ Изменить текст", "mail_edit_body")],
            [("➡️ Прикрепить файлы", "mail_to_attach")],
        ])
    )
    await callback.answer()


@router.callback_query(Mail.choose_template, F.data == "mail_manual")
async def mail_manual(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Тема письма?", reply_markup=cancel_kb())
    await state.set_state(Mail.subject)
    await callback.answer()


@router.callback_query(Mail.choose_template, F.data == "mail_cancel_start")
async def mail_cancel_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено")


@router.callback_query(Mail.choose_template, F.data == "mail_edit_subject")
async def mail_edit_subject(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи новую тему:", reply_markup=cancel_kb())
    await state.set_state(Mail.subject)
    await callback.answer()


@router.callback_query(Mail.choose_template, F.data == "mail_edit_body")
async def mail_edit_body(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи новый текст:", reply_markup=cancel_kb())
    await state.set_state(Mail.body)
    await callback.answer()


@router.callback_query(Mail.choose_template, F.data == "mail_to_attach")
async def mail_to_attach(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📎 Прикрепи аудиофайлы (можно несколько).\n\n"
        f"Лимит: {MAX_ATTACHMENT_MB} MB на всё письмо.\n"
        "Когда закончишь — нажми «✅ Готово».",
        reply_markup=kb([["✅ Готово", "❌ Отмена"]])
    )
    await state.set_state(Mail.attach)
    await callback.answer()


@router.message(Mail.subject)
async def mail_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(subject=message.text.strip())

    data = await state.get_data()
    if data.get("body"):
        await message.answer(
            "📎 Прикрепи аудиофайлы или «✅ Готово».",
            reply_markup=kb([["✅ Готово", "❌ Отмена"]])
        )
        await state.set_state(Mail.attach)
    else:
        await message.answer("Текст письма?", reply_markup=cancel_kb())
        await state.set_state(Mail.body)


@router.message(Mail.body)
async def mail_body(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return await cancel(message, state)
    await state.update_data(body=message.text.strip(), attachments=[])
    await message.answer(
        "📎 Прикрепи аудиофайлы (можно несколько).\n\n"
        f"Лимит: {MAX_ATTACHMENT_MB} MB на всё письмо.\n"
        "Когда закончишь — нажми «✅ Готово».",
        reply_markup=kb([["✅ Готово", "❌ Отмена"]])
    )
    await state.set_state(Mail.attach)


@router.message(Mail.attach, F.audio | F.document)
async def mail_attach(message: types.Message, state: FSMContext):
    file_obj = message.audio or message.document
    if not file_obj:
        return await message.answer("Это не файл. Отправь mp3/wav.")

    size = file_obj.file_size or 0
    name = file_obj.file_name or f"audio_{message.message_id}.mp3"

    data = await state.get_data()
    attachments = data.get("attachments", [])
    total = sum(a["size"] for a in attachments) + size
    max_bytes = MAX_ATTACHMENT_MB * 1024 * 1024

    if total > max_bytes:
        return await message.answer(
            f"⚠️ Не влезет. Уже: {sum(a['size'] for a in attachments)/1024/1024:.1f} MB, "
            f"новый: {size/1024/1024:.1f} MB, лимит: {MAX_ATTACHMENT_MB} MB."
        )

    file_path = os.path.join(TEMP_DIR, f"{message.message_id}_{name}")
    await message.answer(f"📥 Скачиваю {name}...")

    try:
        file = await message.bot.get_file(file_obj.file_id)
        await download_file_stream(file.file_path, file_path)
    except Exception as e:
        return await message.answer(f"❌ Ошибка скачивания: {e}")

    attachments.append({"path": file_path, "name": name, "size": size})
    await state.update_data(attachments=attachments)

    await message.answer(
        f"✅ Добавлен: {name} ({size/1024/1024:.1f} MB)\n"
        f"Всего: {len(attachments)} файл(а), {total/1024/1024:.1f} MB / {MAX_ATTACHMENT_MB} MB\n\n"
        f"Ещё файл или «✅ Готово»?"
    )


@router.message(Mail.attach, F.text == "✅ Готово")
async def mail_attach_done(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await show_confirm(message, state, data, data.get("attachments", []))


@router.message(Mail.attach, F.text == "❌ Отмена")
async def mail_attach_cancel(message: types.Message, state: FSMContext):
    data = await state.get_data()
    for att in data.get("attachments", []):
        if os.path.exists(att["path"]):
            os.remove(att["path"])
    await cancel(message, state)


async def show_confirm(message, state, data, attachments):
    user_id = message.from_user.id
    c = repository.get_contact_by_id(user_id, data["contact_id"])

    text = (
        f"✉️ Проверь письмо:\n\n"
        f"Кому: {c['name']} <{c['email']}>\n"
        f"Тема: {data['subject']}\n\n"
        f"{data['body']}\n\n"
    )

    if attachments:
        total_size = sum(a["size"] for a in attachments) / 1024 / 1024
        text += f"📎 Вложения ({len(attachments)}, {total_size:.1f} MB):\n"
        for att in attachments:
            text += f"  • {att['name']} ({att['size']/1024/1024:.1f} MB)\n"
    else:
        text += "📎 Без вложений"

    await state.update_data(attachments=attachments)
    await state.set_state(Mail.confirm)

    await message.answer(text, reply_markup=inline([
        [("✅ Отправить", "mail_send")],
        [("❌ Отмена", "mail_cancel")],
    ]))


@router.callback_query(F.data == "mail_send")
async def mail_send(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    await state.clear()

    cid = data["contact_id"]
    c = repository.get_contact_by_id(user_id, cid)
    attachments = data.get("attachments", [])

    await callback.message.edit_text("📤 Отправляю...")
    await callback.answer()

    # Пока используем Gmail из config (твой), позже — из gmail_integrations
    ok, err = mailer.send_email(
        to=c["email"],
        subject=data["subject"],
        body=data["body"],
        attachments=attachments,
    )

    if not ok:
        return await callback.message.edit_text(f"❌ Ошибка отправки:\n\n{err}")

    action_type = "sent_beat" if attachments else "wrote"
    action_label = "отправил бит" if attachments else "написал"

    repository.update_contact_after_email(user_id, cid, action_type)
    repository.add_history(
        user_id,
        cid,
        action=action_label,
        beat_name=", ".join(a["name"] for a in attachments) if attachments else None,
        comment=data["subject"]
    )

    for att in attachments:
        if os.path.exists(att["path"]):
            os.remove(att["path"])

    att_info = "—"
    if attachments:
        att_info = f"{len(attachments)} файл(а): {', '.join(a['name'] for a in attachments)}"

    await callback.message.edit_text(
        f"✅ Письмо отправлено!\n\n"
        f"Кому: {c['name']} <{c['email']}>\n"
        f"Тема: {data['subject']}\n"
        f"Вложения: {att_info}\n\n"
        f"Статус: ждёшь ответа\nНапомню через 3 дня"
    )
    await callback.message.answer("Меню:", reply_markup=main_menu())


@router.callback_query(F.data == "mail_cancel")
async def mail_cancel(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for att in data.get("attachments", []):
        if os.path.exists(att["path"]):
            os.remove(att["path"])
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.message.answer("Меню:", reply_markup=main_menu())
    await callback.answer()


# ═══════════════════════════════════════
#  ИСТОРИЯ
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("history:"))
async def show_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cid = int(callback.data.split(":")[1])
    rows = repository.get_history(user_id, cid)

    if not rows:
        return await callback.answer("История пуста", show_alert=True)

    text = "📜 История:\n\n"
    for r in rows:
        text += f"• {r['sent_at']} — {r['action']}"
        if r["beat_name"]:
            text += f" ({r['beat_name']})"
        text += "\n"

    await callback.message.answer(text)
    await callback.answer()