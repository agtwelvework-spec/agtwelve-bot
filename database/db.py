import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            instagram TEXT,
            source TEXT,
            genre TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_contact_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            next_reminder_at DATETIME,
            last_action_type TEXT DEFAULT 'none',
            waiting_on TEXT DEFAULT 'nobody'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            beat_name TEXT,
            comment TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            subject TEXT,
            body TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gmail_integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            refresh_token TEXT NOT NULL,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Индексы
    cur.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_contacts_reminder ON contacts(user_id, next_reminder_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gmail_user ON gmail_integrations(user_id)")

    conn.commit()
    conn.close()
    print("База готова.", flush=True)
