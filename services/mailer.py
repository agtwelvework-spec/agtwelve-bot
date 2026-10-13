import os
import base64
from email.message import EmailMessage
from email.utils import formataddr

from googleapiclient.errors import HttpError

from config import SENDER_NAME
from services.gmail_oauth import get_gmail_service


def send_email(user_id, user_email, refresh_token, to, subject, body, attachments=None):
    """
    Отправить письмо через Gmail конкретного юзера.
    user_id, user_email, refresh_token — данные юзера.
    """
    try:
        service = get_gmail_service(refresh_token)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((SENDER_NAME, user_email))
        msg["To"] = to
        msg.set_content(body)

        if attachments:
            for att in attachments:
                path = att["path"]
                name = att["name"]

                if not os.path.exists(path):
                    continue

                with open(path, "rb") as f:
                    data = f.read()

                ext = name.lower().rsplit(".", 1)[-1]
                if ext == "mp3":
                    maintype, subtype = "audio", "mpeg"
                elif ext == "wav":
                    maintype, subtype = "audio", "wav"
                elif ext == "ogg":
                    maintype, subtype = "audio", "ogg"
                elif ext == "m4a":
                    maintype, subtype = "audio", "mp4"
                else:
                    maintype, subtype = "application", "octet-stream"

                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return True, None

    except HttpError as e:
        return False, f"Gmail API error: {e}"
    except Exception as e:
        return False, str(e)
