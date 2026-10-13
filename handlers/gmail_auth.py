from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import repository
from services.gmail_oauth import get_auth_url
from keyboards.main_menu import main_menu

router = Router()


@router.message(Command("connect_gmail"))
@router.message(F.text == "🔗 Gmail")
async def connect_gmail(message: types.Message):
    user_id = message.from_user.id
    integration = repository.get_gmail_integration(user_id)

    if integration:
        await message.answer(
            f"✅ Gmail уже подключён:\n"
            f"📧 {integration['email']}\n\n"
            f"Хочешь переподключить?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Переподключить", callback_data="gmail_reconnect")],
                [InlineKeyboardButton(text="🗑 Отключить", callback_data="gmail_disconnect")],
            ])
        )
        return

    await message.answer(
        "🔗 Чтобы отправлять письма с твоего Gmail, надо подключить аккаунт.\n\n"
        "Нажми кнопку ниже — откроется Google. Выбери **свой** аккаунт и разреши отправку.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Подключить Gmail", callback_data="gmail_connect")],
        ])
    )


@router.callback_query(F.data == "gmail_connect")
async def gmail_connect_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    try:
        auth_url = get_auth_url(user_id)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "🔗 Открой ссылку, выбери **свой** Gmail, разреши доступ:\n\n"
        f"{auth_url}\n\n"
        "После разрешения вернись сюда и напиши /start.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть Google", url=auth_url)],
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "gmail_reconnect")
async def gmail_reconnect(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    repository.delete_gmail_integration(user_id)
    await gmail_connect_cb(callback)


@router.callback_query(F.data == "gmail_disconnect")
async def gmail_disconnect(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    repository.delete_gmail_integration(user_id)
    await callback.message.edit_text("🗑 Gmail отключён.")
    await callback.message.answer("Меню:", reply_markup=main_menu())
    await callback.answer()
