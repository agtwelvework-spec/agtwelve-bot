import os
import base64
import time
import asyncio
import threading
import urllib.request
from flask import Flask, request, redirect
from aiogram import Bot, Dispatcher
from config import TOKEN
from database.db import init_db
from database import repository
from handlers import start, contacts, templates, reminders, gmail_auth
from services.gmail_oauth import exchange_code

app = Flask(__name__)


def restore_credentials():
    """Восстанавливает credentials.json из env (base64)."""
    creds_b64 = os.environ.get("GMAIL_CREDENTIALS_B64")
    if creds_b64 and not os.path.exists("credentials.json"):
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))
        print("✓ credentials.json восстановлен")


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
        time.sleep(600)


@app.route("/")
def index():
    return "Bot is running"


@app.route("/health")
def health():
    return "OK", 200


@app.route("/oauth/callback")
def oauth_callback():
    """Google возвращает сюда с code и state."""
    code = request.args.get("code")
    user_id = request.args.get("state")

    if not code or not user_id:
        return "Ошибка: нет code или state", 400

    try:
        refresh_token, email = exchange_code(code)
        repository.save_gmail_integration(int(user_id), refresh_token, email)
        return """
        <html><body style="font-family:sans-serif;text-align:center;padding:50px">
        <h1>✅ Gmail подключён!</h1>
        <p>Можешь закрыть это окно и вернуться в Telegram.</p>
        </body></html>
        """
    except Exception as e:
        return f"Ошибка: {e}", 500


def run_bot():
    async def main():
        init_db()
        restore_credentials()
        bot = Bot(token=TOKEN)
        dp = Dispatcher()
        dp.include_router(start.router)
        dp.include_router(contacts.router)
        dp.include_router(templates.router)
        dp.include_router(reminders.router)
        dp.include_router(gmail_auth.router)
        print("Бот запущен...")
        await dp.start_polling(bot, handle_signals=False)

    asyncio.run(main())


if __name__ == "__main__":
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
