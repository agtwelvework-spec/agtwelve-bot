import os
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from database import repository
from keyboards.main_menu import main_menu
from services import campaign_manager

router = Router()

# ═══════════════════════════════════════
#  КЛАВИАТУРЫ
# ═══════════════════════════════════════

def campaign_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Добавить лупы", callback_data="drop_add_files")],
        [InlineKeyboardButton(text="🎯 Выбрать жанр", callback_data="drop_set_genre")],
        [InlineKeyboardButton(text="📝 Текст письма", callback_data="drop_set_template")],
        [InlineKeyboardButton(text="👀 Проверить и разослать", callback_data="drop_review")],
        [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="drop_cancel")]
    ])

def inline(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])

# ═══════════════════════════════════════
#  СОСТОЯНИЯ
# ═══════════════════════════════════════

class DropState(StatesGroup):
    waiting_genre = State()
    waiting_template = State()
    waiting_files = State()

# ═══════════════════════════════════════
#  ГЛАВНОЕ МЕНЮ РАССЫЛКИ
# ═══════════════════════════════════════

@router.message(Command("drop"))
@router.message(F.text == "📨 Weekly Drop")
async def start_drop(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    # Ищем активную черновую рассылку или создаем новую
    campaign = campaign_manager.get_active_draft(user_id)
    if not campaign:
        cid = campaign_manager.create_campaign(user_id)
        campaign = campaign_manager.get_active_draft(user_id)
    else:
        cid = campaign["id"]

    stats = campaign_manager.get_campaign_stats(cid)
    genre = campaign["genre_filter"] or "Не выбран"
    
    text = (
        f"📨 **Твоя корзина рассылки (Weekly Drop)**\n\n"
        f"🎯 Жанр: {genre}\n"
        f"📎 Файлов добавлено: {stats['total']} (пока считаем как получатели)\n" # Упрощенно
        f"👥 Получателей: {stats['total']}\n\n"
        f"Закидывай сюда лупы в течение недели. В пятницу в 18:00 они улетят."
    )
    
    await message.answer(text, reply_markup=campaign_menu_kb(), parse_mode="Markdown")

# ═══════════════════════════════════════
#  НАСТРОЙКА ЖАНРА
# ═══════════════════════════════════════

@router.callback_query(F.data == "drop_set_genre")
async def drop_set_genre(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎯 Введи жанр (например: Trap, Drill, R&B).\n"
        "Бот отправит лупы только тем контактам, у кого в карточке указан этот жанр.\n\n"
        "Если хочешь отправить **всем** — напиши `Все`."
    )
    await state.set_state(DropState.waiting_genre)
    await callback.answer()

@router.message(DropState.waiting_genre)
async def drop_genre_save(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    genre = message.text.strip()
    if genre.lower() == "все":
        genre = None
        
    campaign = campaign_manager.get_active_draft(user_id)
    campaign_manager.update_campaign_genre(campaign["id"], genre)
    
    await state.clear()
    await message.answer("✅ Жанр сохранен!", reply_markup=main_menu())
    await start_drop(message, state) # перерисовываем меню

# ═══════════════════════════════════════
#  НАСТРОЙКА ТЕКСТА ПИСЬМА
# ═══════════════════════════════════════

@router.callback_query(F.data == "drop_set_template")
async def drop_set_template(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    templates = repository.get_all_templates(user_id)
    
    rows = [[("✏️ Написать с нуля", "drop_manual_text")]]
    for t in templates:
        rows.append([(f"📋 {t['name']}", f"drop_use_tpl:{t['id']}")])
    rows.append([("⬅️ Назад", "drop_back")])
    
    await callback.message.edit_text("📝 Выбери шаблон письма или напиши с нуля:", reply_markup=inline(rows))
    await callback.answer()

@router.callback_query(F.data == "drop_manual_text")
async def drop_manual_text(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи текст письма (он уйдет всем получателям):")
    await state.set_state(DropState.waiting_template)
    await callback.answer()

@router.message(DropState.waiting_template)
async def drop_text_save(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    campaign = campaign_manager.get_active_draft(user_id)
    
    conn = campaign_manager.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE campaigns SET body = ? WHERE id = ?", (message.text.strip(), campaign["id"]))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("✅ Текст сохранен!", reply_markup=main_menu())
    await start_drop(message, state)

# ═══════════════════════════════════════
#  ДОБАВЛЕНИЕ ФАЙЛОВ (ЛУПОВ)
# ═══════════════════════════════════════

@router.callback_query(F.data == "drop_add_files")
async def drop_add_files(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📎 Отправляй сюда аудиофайлы (mp3/wav).\n"
        "Можно отправлять по одному или пачкой.\n\n"
        "Когда закончишь — напиши /drop, чтобы вернуться в меню."
    )
    await state.set_state(DropState.waiting_files)
    await callback.answer()

@router.message(DropState.waiting_files, F.audio | F.document)
async def drop_file_received(message: types.Message, state: FSMContext):
    file_obj = message.audio or message.document
    if not file_obj:
        return await message.answer("Это не файл. Отправь mp3/wav.")

    user_id = message.from_user.id
    campaign = campaign_manager.get_active_draft(user_id)
    
    name = file_obj.file_name or f"audio_{message.message_id}.mp3"
    size = file_obj.file_size or 0
    
    if size > 20 * 1024 * 1024: # Лимит Telegram 20MB
         return await message.answer("⚠️ Файл больше 20 MB, Telegram не даст его скачать боту.")

    await message.answer(f"📥 Скачиваю {name}...")
    
    try:
        # Скачиваем файл во временную папку
        os.makedirs("data/temp", exist_ok=True)
        file_path = os.path.join("data/temp", f"{message.message_id}_{name}")
        
        file = await message.bot.get_file(file_obj.file_id)
        await message.bot.download_file(file.file_path, file_path)
        
        # Сохраняем в базу (пока просто путь, но в будущем можно BLOB)
        campaign_manager.add_attachment_to_campaign(campaign["id"], file_path, name, b"dummy") # Заглушка под BLOB
        
        await message.answer(f"✅ {name} добавлен в корзину рассылки!")
    except Exception as e:
        await message.answer(f"❌ Ошибка скачивания: {e}")

# ═══════════════════════════════════════
#  ПРОВЕРКА И ЗАПУСК
# ═══════════════════════════════════════

@router.callback_query(F.data == "drop_review")
async def drop_review(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    campaign = campaign_manager.get_active_draft(user_id)
    
    if not campaign:
        return await callback.answer("Нет активной рассылки", show_alert=True)
        
    genre = campaign["genre_filter"] or "Все контакты"
    
    # Подтягиваем контакты
    total, added = campaign_manager.add_recipients_from_db(campaign["id"], user_id, campaign["genre_filter"])
    
    if added == 0:
        return await callback.message.edit_text(
            f"⚠️ По жанру «{genre}» не найдено ни одного контакта.\n"
            f"Добавь контакты или измени жанр.",
            reply_markup=inline([[("⬅️ Назад", "drop_back")]])
        )
        
    await callback.message.edit_text(
        f"📊 **Проверка рассылки:**\n\n"
        f"🎯 Жанр: {genre}\n"
        f"👥 Получателей: {added}\n"
        f"📎 Файлов: (посчитаем позже)\n\n"
        f"Всё верно? Отправляем прямо сейчас? (Планировщик запустится сам в пятницу)",
        reply_markup=inline([
            [("🚀 Отправить СЕЙЧАС", "drop_launch_now")],
            [("⬅️ Назад в корзину", "drop_back")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "drop_back")
async def drop_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await start_drop(callback.message, state)
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "drop_launch_now")
async def drop_launch_now(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    campaign = campaign_manager.get_active_draft(user_id)
    
    conn = campaign_manager.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE campaigns SET status = 'running' WHERE id = ?", (campaign["id"],))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "🚀 Рассылка запущена!\n"
        "Бот начнет отправлять письма в фоне. Я сообщу, когда всё закончится."
    )
    await callback.answer()
