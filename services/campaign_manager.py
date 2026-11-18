from datetime import datetime
import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_campaign(user_id, name="Weekly Drop"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO campaigns (user_id, name, status, scheduled_at)
        VALUES (?, ?, 'draft', ?)
    """, (user_id, name, datetime.now().isoformat()))
    camp_id = cur.lastrowid
    conn.commit()
    conn.close()
    return camp_id

def get_active_draft(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM campaigns WHERE user_id = ? AND status = 'draft' ORDER BY id DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_attachment_to_campaign(campaign_id, file_path, file_name, file_bytes):
    """Сохраняет файл в БД (BLOB), чтобы он не пропал."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO campaign_attachments (campaign_id, file_path, file_name, size_bytes)
        VALUES (?, ?, ?, ?)
    """, (campaign_id, file_path, file_name, len(file_bytes)))
    conn.commit()
    conn.close()

def update_campaign_genre(campaign_id, genre_filter):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE campaigns SET genre_filter = ? WHERE id = ?", (genre_filter, campaign_id))
    conn.commit()
    conn.close()

def add_recipients_from_db(campaign_id, user_id, genre_filter):
    """Добавляет в кампанию всех контактов с подходящим жанром."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Ищем контакты по жанру (регистронезависимо)
    query = "SELECT id FROM contacts WHERE user_id = ?"
    params = [user_id]
    if genre_filter:
        query += " AND LOWER(genre) LIKE LOWER(?)"
        params.append(f"%{genre_filter}%")
        
    cur.execute(query, params)
    contacts = cur.fetchall()
    
    added = 0
    for c in contacts:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO campaign_recipients (campaign_id, contact_id)
                VALUES (?, ?)
            """, (campaign_id, c["id"]))
            added += 1
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    return len(contacts), added

def get_campaign_stats(campaign_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT count(*) as total FROM campaign_recipients WHERE campaign_id = ?", (campaign_id,))
    total = cur.fetchone()["total"]
    cur.execute("SELECT count(*) as pending FROM campaign_recipients WHERE campaign_id = ? AND status = 'pending'", (campaign_id,))
    pending = cur.fetchone()["pending"]
    cur.execute("SELECT count(*) as sent FROM campaign_recipients WHERE campaign_id = ? AND status = 'sent'", (campaign_id,))
    sent = cur.fetchone()["sent"]
    conn.close()
    return {"total": total, "pending": pending, "sent": sent}
