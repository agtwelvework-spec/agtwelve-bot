import os
import base64
from email.message import EmailMessage
from email.utils import formataddr

import os
import base64
from email.message import EmailMessage
from email.utils import formataddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, SENDER_NAME

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(to, subject, body, attachments=None):
    """
    attachments: список dict {'path': ..., 'name': ...} или None
    """
    try:
        service = get_gmail_service()

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((SENDER_NAME, "me"))
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

                msg.add_attachment(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=name,
                )

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        return True, None

    except HttpError as e:
        return False, f"Gmail API error: {e}"
    except Exception as e:
        return False, str(e)