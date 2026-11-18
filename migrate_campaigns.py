import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("→ Начинаю миграцию для рассылок...")

# 1. Таблица кампаний (сама рассылка)
cur.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        template_id INTEGER,
        subject TEXT,
        body TEXT,
        genre_filter TEXT,               -- какой жанр выбран (Trap, Drill и т.д.)
        status TEXT DEFAULT 'draft',     -- draft | running | done
        scheduled_at DATETIME,           -- когда отправлять
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")

# 2. Таблица получателей (кто входит в кампанию)
cur.execute("""
    CREATE TABLE IF NOT EXISTS campaign_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        contact_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',   -- pending | sent | failed
        sent_at DATETIME,
        error TEXT,
        UNIQUE(campaign_id, contact_id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
    )
""")

# 3. Таблица вложений (файлы, которые ты закидываешь в корзину)
cur.execute("""
    CREATE TABLE IF NOT EXISTS campaign_attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        size_bytes INTEGER,
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
    )
""")

# Индексы для быстрой работы
cur.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_recipients_status ON campaign_recipients(campaign_id, status)")

conn.commit()
conn.close()

print("✅ Миграция для рассылок завершена!")
