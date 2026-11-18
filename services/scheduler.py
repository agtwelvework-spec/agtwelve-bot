import asyncio
import os
from datetime import datetime, timedelta
import pytz  # Нужна библиотека для часовых поясов
from database import repository
from services import campaign_manager
from services.mailer import send_email

async def process_campaigns():
    """Фоновая задача: шлет письма и запускает рассылки по расписанию."""
    while True:
        try:
            # 1. ПРОВЕРКА РАСПИСАНИЯ (Автозапуск в пятницу)
            msk_tz = pytz.timezone('Europe/Moscow')
            now_msk = datetime.now(msk_tz)
            
            # Если сегодня пятница (4 - это пятница в Python) и время >= 18:00
            if now_msk.weekday() == 4 and now_msk.hour >= 18:
                conn = campaign_manager.get_connection()
                cur = conn.cursor()
                # Ищем черновики, которые ждут отправки
                cur.execute("SELECT * FROM campaigns WHERE status = 'draft'")
                drafts = cur.fetchall()
                
                for draft in drafts:
                    # Проверяем, есть ли в черновике хоть один получатель
                    cur.execute("SELECT count(*) as c FROM campaign_recipients WHERE campaign_id = ?", (draft["id"],))
                    if cur.fetchone()["c"] > 0:
                        cur.execute("UPDATE campaigns SET status = 'running' WHERE id = ?", (draft["id"],))
                        print(f"⏰ Наступило время! Запускаю рассылку #{draft['id']} по расписанию.")
                conn.commit()
                conn.close()

            # 2. ОТПРАВКА ПИСЕМ (Код из предыдущего шага)
            conn = campaign_manager.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM campaigns WHERE status = 'running'")
            campaigns = cur.fetchall()
            
            for camp in campaigns:
                cur.execute("""
                    SELECT cr.id as recipient_id, cr.contact_id, c.email, c.name 
                    FROM campaign_recipients cr
                    JOIN contacts c ON c.id = cr.contact_id
                    WHERE cr.campaign_id = ? AND cr.status = 'pending'
                    LIMIT 1
                """, (camp["id"],))
                recipient = cur.fetchone()
                
                if not recipient:
                    cur.execute("UPDATE campaigns SET status = 'done' WHERE id = ?", (camp["id"],))
                    conn.commit()
                    continue
                
                integration = repository.get_gmail_integration(camp["user_id"])
                if not integration:
                    cur.execute("UPDATE campaigns SET status = 'failed' WHERE id = ?", (camp["id"],))
                    conn.commit()
                    continue
                
                cur.execute("SELECT * FROM campaign_attachments WHERE campaign_id = ?", (camp["id"],))
                attachments = cur.fetchall()
                att_list = []
                for att in attachments:
                    if os.path.exists(att["file_path"]):
                        att_list.append({"path": att["file_path"], "name": att["file_name"], "size": att["size_bytes"]})
                
                body = camp["body"] or "Привет! Свежие лупы во вложении."
                body = body.replace("{name}", recipient["name"] or "")
                
                print(f"📤 Автоотправка для {recipient['email']}...")
                
                ok, err = await asyncio.to_thread(
                    send_email,
                    user_id=camp["user_id"],
                    user_email=integration["email"],
                    refresh_token=integration["refresh_token"],
                    to=recipient["email"],
                    subject=camp["name"] or "Weekly Drop",
                    body=body,
                    attachments=att_list
                )
                
                if ok:
                    cur.execute("UPDATE campaign_recipients SET status = 'sent', sent_at = ? WHERE id = ?", 
                                (datetime.now().isoformat(), recipient["recipient_id"]))
                    repository.add_history(camp["user_id"], recipient["contact_id"], "Weekly Drop", comment="Авторассылка")
                else:
                    cur.execute("UPDATE campaign_recipients SET status = 'failed', error = ? WHERE id = ?", 
                                (str(err), recipient["recipient_id"]))
                
                conn.commit()
                await asyncio.sleep(3) 
                
            conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка в планировщике: {e}")
            
        await asyncio.sleep(60)

def start_scheduler():
    asyncio.create_task(process_campaigns())
