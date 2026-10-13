import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from database.db import init_db
from handlers import start, contacts, templates, reminders, gmail_auth


async def main():
    init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(contacts.router)
    dp.include_router(templates.router)
    dp.include_router(reminders.router)
    dp.include_router(gmail_auth.router)
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
