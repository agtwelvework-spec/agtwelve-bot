import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
]
REDIRECT_URI = "https://agtwelve-bot.onrender.com/oauth/callback"
CREDENTIALS_FILE = "credentials.json"

def get_auth_url(user_id):
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,   # ← вот это
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=str(user_id),
    )
    return auth_url


def exchange_code(code):
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,   # ← и вот это
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Получаем email юзера
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress")

    return creds.refresh_token, email


def get_gmail_service(refresh_token):
    """Получить Gmail-сервис по refresh_token юзера."""
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=json.load(open(CREDENTIALS_FILE))["web"]["client_id"],
        client_secret=json.load(open(CREDENTIALS_FILE))["web"]["client_secret"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)
