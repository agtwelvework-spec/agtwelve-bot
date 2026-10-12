import sqlite3
from config import DB_PATH, ADMIN_ID

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def column_exists(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return column in [r[1] for r in cur.fetchall()]

print("→ Начинаю миграцию...\n")

# ─── contacts ───
if not column_exists("contacts", "user_id"):
    cur.execute("ALTER TABLE contacts ADD COLUMN user_id INTEGER")
    cur.execute("UPDATE contacts SET user_id = ? WHERE user_id IS NULL", (ADMIN_ID,))
    print("  ✓ contacts.user_id добавлен")
else:
    print("  = contacts.user_id уже есть")

# ─── history ───
if not column_exists("history", "user_id"):
    cur.execute("ALTER TABLE history ADD COLUMN user_id INTEGER")
    cur.execute("UPDATE history SET user_id = ? WHERE user_id IS NULL", (ADMIN_ID,))
    print("  ✓ history.user_id добавлен")
else:
    print("  = history.user_id уже есть")

# ─── templates ───
if not column_exists("templates", "user_id"):
    cur.execute("ALTER TABLE templates ADD COLUMN user_id INTEGER")
    cur.execute("UPDATE templates SET user_id = ? WHERE user_id IS NULL", (ADMIN_ID,))
    print("  ✓ templates.user_id добавлен")
else:
    print("  = templates.user_id уже есть")

# ─── gmail_integrations ───
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
print("  ✓ gmail_integrations готова")

# ─── Индексы ───
cur.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_contacts_reminder ON contacts(user_id, next_reminder_at)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_gmail_user ON gmail_integrations(user_id)")
print("  ✓ индексы созданы")

conn.commit()
conn.close()

print(f"\n✅ Миграция завершена!")
print(f"→ Существующие данные привязаны к user_id = {ADMIN_ID}")