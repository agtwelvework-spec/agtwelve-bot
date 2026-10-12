import os
from pathlib import Path

# Локально — читаем из .env
if Path(".env").exists():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

DB_PATH = "data/contacts.db"
DEFAULT_REMINDER_DAYS = 3
MAX_ATTACHMENT_MB = 25

# Gmail API
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"
SENDER_NAME = "Beats by agtwelve"