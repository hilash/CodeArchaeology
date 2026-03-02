"""Gmail OAuth2 authentication module."""

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def get_credentials() -> Credentials:
    """Get valid Gmail API credentials, refreshing or creating as needed."""
    creds = None

    # Load existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"ERROR: {CREDENTIALS_FILE} not found!")
                print()
                print("To set up Gmail API access:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a project (or select existing)")
                print("3. Enable the Gmail API")
                print("4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID")
                print("5. Choose 'Desktop application' as the type")
                print("6. Download the JSON and save it as:")
                print(f"   {CREDENTIALS_FILE}")
                sys.exit(1)

            print("Opening browser for Gmail authorization...")
            print("(Grant read-only access to your Gmail)")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        TOKEN_FILE.write_text(creds.to_json())
        # Restrict file permissions
        TOKEN_FILE.chmod(0o600)
        print("Token saved.")

    return creds


def get_gmail_service():
    """Get an authenticated Gmail API service instance."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    return service
