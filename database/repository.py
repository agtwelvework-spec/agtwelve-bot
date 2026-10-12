from datetime import datetime, timedelta
from database.db import get_connection
from config import DEFAULT_REMINDER_DAYS


# ═══════════════════════════════════════
#  КОНТАКТЫ
# ═══════════════════════════════════════

def add_contact(user_id, name, email=None, instagram=None, source=None, genre=None, notes=None):
    conn = get_connection()
    cur = conn.cursor()
    next_reminder = (datetime.now() + timedelta(days=DEFAULT_REMINDER_DAYS)).isoformat()
    cur.execute("""
        INSERT INTO contacts (user_id, name, email, instagram, source, genre, notes, next_reminder_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, email, instagram, source, genre, notes, next_reminder))
    contact_id = cur.lastrowid
    conn.commit()
    conn.close()
    return contact_id


def get_all_contacts(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY last_contact_at DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_contact_by_id(user_id, contact_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE id = ? AND user_id = ?", (contact_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row


def search_contacts(user_id, query):
    conn = get_connection()
    cur = conn.cursor()
    like = f"%{query}%"
    cur.execute("""
        SELECT DISTINCT c.* FROM contacts c
        LEFT JOIN history h ON h.contact_id = c.id
        WHERE c.user_id = ?
          AND (c.name LIKE ?
            OR c.email LIKE ?
            OR c.instagram LIKE ?
            OR c.source LIKE ?
            OR c.genre LIKE ?
            OR c.notes LIKE ?
            OR h.action LIKE ?
            OR h.beat_name LIKE ?
            OR h.comment LIKE ?)
        ORDER BY c.last_contact_at DESC
        LIMIT 20
    """, (user_id, like, like, like, like, like, like, like, like, like))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_contact_field(user_id, contact_id, field, value):
    allowed = {"name", "email", "instagram", "source", "genre", "notes"}
    if field not in allowed:
        raise ValueError(f"Нельзя обновлять поле: {field}")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE contacts SET {field} = ? WHERE id = ? AND user_id = ?",
        (value, contact_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_contact(user_id, contact_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE contact_id = ? AND user_id = ?", (contact_id, user_id))
    cur.execute("DELETE FROM contacts WHERE id = ? AND user_id = ?", (contact_id, user_id))
    conn.commit()
    conn.close()


def update_contact_after_email(user_id, contact_id, action_type):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    next_reminder = (now + timedelta(days=DEFAULT_REMINDER_DAYS)).isoformat()
    cur.execute("""
        UPDATE contacts
        SET last_contact_at = ?, next_reminder_at = ?,
            last_action_type = ?, waiting_on = 'me'
        WHERE id = ? AND user_id = ?
    """, (now.isoformat(), next_reminder, action_type, contact_id, user_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════
#  ИСТОРИЯ
# ═══════════════════════════════════════

def add_history(user_id, contact_id, action, beat_name=None, comment=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO history (user_id, contact_id, action, beat_name, comment)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, contact_id, action, beat_name, comment))
    conn.commit()
    conn.close()


def get_history(user_id, contact_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM history WHERE contact_id = ? AND user_id = ?
        ORDER BY sent_at DESC LIMIT ?
    """, (contact_id, user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


# ═══════════════════════════════════════
#  ТЕМПЛЕЙТЫ
# ═══════════════════════════════════════

def add_template(user_id, name, subject, body):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO templates (user_id, name, subject, body)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, subject, body))
    template_id = cur.lastrowid
    conn.commit()
    conn.close()
    return template_id


def get_all_templates(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_template_by_id(user_id, template_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM templates WHERE id = ? AND user_id = ?", (template_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row


def update_template(user_id, template_id, name, subject, body):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE templates SET name = ?, subject = ?, body = ?
        WHERE id = ? AND user_id = ?
    """, (name, subject, body, template_id, user_id))
    conn.commit()
    conn.close()


def delete_template(user_id, template_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════
#  REMINDERS
# ═══════════════════════════════════════

def get_due_contacts(user_id):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute("""
        SELECT * FROM contacts
        WHERE user_id = ? AND waiting_on = 'me' AND next_reminder_at <= ?
        ORDER BY next_reminder_at ASC
    """, (user_id, now))
    waiting_me = cur.fetchall()

    three_days = (datetime.now() - timedelta(days=3)).isoformat()
    cur.execute("""
        SELECT * FROM contacts
        WHERE user_id = ? AND waiting_on = 'him' AND last_contact_at <= ?
        ORDER BY last_contact_at ASC
    """, (user_id, three_days))
    waiting_him = cur.fetchall()

    week = (datetime.now() - timedelta(days=7)).isoformat()
    cur.execute("""
        SELECT * FROM contacts
        WHERE user_id = ?
          AND (waiting_on = 'nobody' OR waiting_on IS NULL)
          AND last_contact_at <= ?
        ORDER BY last_contact_at ASC
    """, (user_id, week))
    silent = cur.fetchall()

    conn.close()
    return waiting_me, waiting_him, silent


def snooze_all(user_id, days=3):
    conn = get_connection()
    cur = conn.cursor()
    new_date = (datetime.now() + timedelta(days=days)).isoformat()
    cur.execute("""
        UPDATE contacts SET next_reminder_at = ?
        WHERE user_id = ? AND next_reminder_at IS NOT NULL AND next_reminder_at <= ?
    """, (new_date, user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def set_status(user_id, contact_id, waiting_on, last_action_type=None):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    next_reminder = (now + timedelta(days=3)).isoformat()

    if last_action_type:
        cur.execute("""
            UPDATE contacts
            SET waiting_on = ?, last_action_type = ?,
                last_contact_at = ?, next_reminder_at = ?
            WHERE id = ? AND user_id = ?
        """, (waiting_on, last_action_type, now.isoformat(), next_reminder, contact_id, user_id))
    else:
        cur.execute("""
            UPDATE contacts SET waiting_on = ?, next_reminder_at = ?
            WHERE id = ? AND user_id = ?
        """, (waiting_on, next_reminder, contact_id, user_id))

    conn.commit()
    conn.close()


def check_beat_sent(user_id, contact_id, beat_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sent_at, beat_name FROM history
        WHERE user_id = ? AND contact_id = ? AND beat_name LIKE ?
        ORDER BY sent_at DESC LIMIT 1
    """, (user_id, contact_id, f"%{beat_name}%"))
    row = cur.fetchone()
    conn.close()
    return row


# ═══════════════════════════════════════
#  GMAIL-ИНТЕГРАЦИИ
# ═══════════════════════════════════════

def save_gmail_integration(user_id, refresh_token, email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gmail_integrations (user_id, refresh_token, email)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            refresh_token = excluded.refresh_token,
            email = excluded.email,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, refresh_token, email))
    conn.commit()
    conn.close()


def get_gmail_integration(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gmail_integrations WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def delete_gmail_integration(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM gmail_integrations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()