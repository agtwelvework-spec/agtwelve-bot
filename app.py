import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from config import TOKEN
from database.db import init_db
from handlers import start, contacts, templates, reminders

# ─── Flask ───
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running"

@app.route("/health")
def health():
    return "OK", 200


# ─── Бот в отдельном потоке ───
def run_bot():
    async def main():
        init_db()
        bot = Bot(token=TOKEN)
        dp = Dispatcher()
        dp.include_router(start.router)
        dp.include_router(contacts.router)
        dp.include_router(templates.router)
        dp.include_router(reminders.router)
        print("Бот запущен...")
        await dp.start_polling(bot)

    asyncio.run(main())


# ─── Запуск ───
if __name__ == "__main__":
    # Бот в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Flask в основном потоке (Render видит порт)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)