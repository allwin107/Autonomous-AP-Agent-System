import os
import base64
from typing import List, Dict, Any, Optional
from email.message import EmailMessage
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailTool:
    def __init__(self, token_path: str = 'token.json', credentials_path: str = 'credentials.json'):
        self.creds = None
        self.service = None
        self.token_path = token_path
        self.credentials_path = credentials_path

    def authenticate(self):
        """Authenticate with Gmail API."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    # If no credentials file, we can't authenticate (unless mocked)
                    print(f"Warning: {self.credentials_path} not found. GmailTool specific operations will fail unless mocked.")
                    return
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
        except HttpError as error:
            print(f'An error occurred: {error}')
            self.service = None

    def fetch_unread_invoices(self, query: str = "subject:invoice OR has:attachment label:INBOX is:unread") -> List[Dict[str, Any]]:
        """Fetch unread emails matching the query."""
        if not self.service:
            self.authenticate()
            if not self.service:
                return []

        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                txt = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                emails.append(txt)
            
            return emails
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def extract_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Extract attachments from a message ID."""
        if not self.service:
            self.authenticate()
            if not self.service:
                return []

        try:
            message = self.service.users().messages().get(userId='me', id=message_id).execute()
            parts = message.get('payload', {}).get('parts', [])
            
            found_attachments = []
            for part in parts:
                if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
                    attachment = self.service.users().messages().attachments().get(
                        userId='me', messageId=message_id, id=part['body']['attachmentId']
                    ).execute()
                    
                    data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                    
                    found_attachments.append({
                        "filename": part['filename'],
                        "mimeType": part['mimeType'],
                        "data": data,
                        "size": len(data)
                    })
            
            return found_attachments
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def mark_as_read(self, message_id: str):
        """Remove UNREAD label from message."""
        if not self.service:
            self.authenticate()
            if not self.service:
                return

        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except HttpError as error:
            print(f'An error occurred: {error}')

gmail_tool = GmailTool()
