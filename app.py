import os
import time
import base64
import asyncio
import threading
import urllib.request
from flask import Flask
from aiogram import Bot, Dispatcher
from config import TOKEN
from database.db import init_db
from handlers import start, contacts, templates, reminders

app = Flask(__name__)


def self_ping():
    """Пингует сам себя каждые 10 минут, чтобы Render не усыплял."""
    time.sleep(60)
    url = "https://agtwelve-bot.onrender.com/health"
    while True:
        try:
            urllib.request.urlopen(url, timeout=10)
            print("✓ self-ping OK")
        except Exception as e:
            print(f"⚠️ self-ping failed: {e}")
        time.sleep(600)  # 10 минут


@app.route("/")
def index():
    return "Bot is running"


@app.route("/health")
def health():
    return "OK", 200


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
        await dp.start_polling(bot, handle_signals=False)

    asyncio.run(main())


if __name__ == "__main__":
    # Self-ping в фоне
    threading.Thread(target=self_ping, daemon=True).start()

    # Бот в фоне
    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
