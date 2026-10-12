import sqlite3

conn = sqlite3.connect("data/contacts.db")
cur = conn.cursor()

# Проверяем, какие колонки уже есть
cur.execute("PRAGMA table_info(contacts)")
columns = [row[1] for row in cur.fetchall()]

if "last_action_type" not in columns:
    cur.execute("ALTER TABLE contacts ADD COLUMN last_action_type TEXT DEFAULT 'none'")
    print("+ last_action_type добавлена")
else:
    print("= last_action_type уже есть")

if "waiting_on" not in columns:
    cur.execute("ALTER TABLE contacts ADD COLUMN waiting_on TEXT DEFAULT 'nobody'")
    print("+ waiting_on добавлена")
else:
    print("= waiting_on уже есть")

conn.commit()
conn.close()
print("OK")