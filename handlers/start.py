from aiogram import Router, types
from aiogram.filters import Command
from keyboards.main_menu import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я твой трекер контактов.\n\nЧто делаем?",
        reply_markup=main_menu()
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Команды:\n"
        "/add — добавить контакт\n"
        "/list — все контакты\n"
        "/start — главное меню"
    )