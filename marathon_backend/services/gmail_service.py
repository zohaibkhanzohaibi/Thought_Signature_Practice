"""
Gmail Service - Per-user OAuth authentication, draft creation, and inbox monitoring.
"""
import os
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# OAuth2 Configuration
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
]

# Path to OAuth client credentials (download from Google Cloud Console)
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/gmail/callback")


class GmailService:
    """Gmail service with per-user OAuth."""
    
    def __init__(self, token_data: Dict = None):
        """
        Initialize with token data from database.
        
        Args:
            token_data: Dict with access_token, refresh_token, expiry, scopes
        """
        self.creds = None
        self.service = None
        self.email_address = None
        
        if token_data:
            self._load_credentials(token_data)
    
    def _load_credentials(self, token_data: Dict):
        """Load credentials from stored token data."""
        try:
            self.creds = Credentials(
                token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._get_client_id(),
                client_secret=self._get_client_secret(),
                scopes=token_data.get("scopes", SCOPES)
            )
            
            # Refresh if expired
            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            
            self.service = build('gmail', 'v1', credentials=self.creds)
            
            # Get authenticated email
            profile = self.service.users().getProfile(userId='me').execute()
            self.email_address = profile.get('emailAddress')
            
        except Exception as e:
            print(f"❌ Gmail auth failed: {e}")
            raise
    
    def _get_client_id(self) -> str:
        """Get OAuth client ID from credentials file."""
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH) as f:
                data = json.load(f)
                return data.get("web", data.get("installed", {})).get("client_id")
        return os.getenv("GMAIL_CLIENT_ID", "")
    
    def _get_client_secret(self) -> str:
        """Get OAuth client secret from credentials file."""
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH) as f:
                data = json.load(f)
                return data.get("web", data.get("installed", {})).get("client_secret")
        return os.getenv("GMAIL_CLIENT_SECRET", "")
    
    @staticmethod
    def get_auth_url(state: str = None) -> str:
        """
        Generate OAuth authorization URL.
        
        Args:
            state: Optional state parameter (e.g., user_id)
            
        Returns:
            Authorization URL for user to visit
        """
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"OAuth credentials not found: {CREDENTIALS_PATH}\n"
                "Download from Google Cloud Console → APIs → Credentials"
            )
        
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        
        return auth_url
    
    @staticmethod
    def exchange_code(code: str) -> Dict:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            
        Returns:
            Dict with access_token, refresh_token, expiry, scopes
        """
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Get email address
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            "email_address": profile.get('emailAddress')
        }
    
    def get_updated_tokens(self) -> Dict:
        """Get current token data (may be refreshed)."""
        if not self.creds:
            return {}
        return {
            "access_token": self.creds.token,
            "refresh_token": self.creds.refresh_token,
            "expiry": self.creds.expiry.isoformat() if self.creds.expiry else None,
            "scopes": list(self.creds.scopes) if self.creds.scopes else SCOPES
        }
    
    # ============================================
    # DRAFT OPERATIONS
    # ============================================

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: str = None,
        in_reply_to: str = None
    ) -> str:
        message = MIMEMultipart()
        # 👇 FIX: Use standard RFC 2822 Title Case for headers
        message['To'] = to
        message['Subject'] = subject
        message['From'] = self.email_address
        
        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
            message['References'] = in_reply_to
        
        message.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                message.attach(part)
                print(f"📎 Attached: {os.path.basename(attachment_path)}")
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = self.service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw}}
        ).execute()
        
        print(f"✅ Draft created: {draft['id']}")
        return draft['id']
    
    def send_draft(self, draft_id: str) -> Dict:
        """Send an existing draft."""
        result = self.service.users().drafts().send(
            userId='me',
            body={'id': draft_id}
        ).execute()
        print(f"✅ Draft sent: {result.get('id')}")
        return result
    
    def get_draft(self, draft_id: str) -> Dict:
        """Get draft details."""
        return self.service.users().drafts().get(
            userId='me',
            id=draft_id
        ).execute()
    
    def list_drafts(self, max_results: int = 10) -> List[Dict]:
        """List user's drafts."""
        result = self.service.users().drafts().list(
            userId='me',
            maxResults=max_results
        ).execute()
        return result.get('drafts', [])
    
    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft."""
        self.service.users().drafts().delete(userId='me', id=draft_id).execute()
        return True
    
    # ============================================
    # INBOX OPERATIONS
    # ============================================
    
    def get_messages(
        self,
        query: str = "",
        label_ids: List[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get messages from inbox.
        
        Args:
            query: Gmail search query (e.g., "is:unread from:recruiter")
            label_ids: Filter by labels (e.g., ["INBOX", "UNREAD"])
            max_results: Maximum messages to return
        """
        params = {"userId": "me", "maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        
        result = self.service.users().messages().list(**params).execute()
        messages = result.get('messages', [])
        
        # Fetch full message details
        detailed = []
        for msg in messages:
            full = self.service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            detailed.append(self._parse_message(full))
        
        return detailed
    
    def _parse_message(self, message: Dict) -> Dict:
        """Parse Gmail message into readable format."""
        # 👇 FIX: Force all header keys to lowercase for safe lookups
        headers = {h['name'].lower(): h['value'] for h in message['payload'].get('headers', [])}
        
        body = self._get_body(message['payload'])
        
        return {
            "id": message['id'],
            "thread_id": message['threadId'],
            "subject": headers.get('subject', ''),
            "from": headers.get('from', ''),
            "to": headers.get('to', ''),
            "date": headers.get('date', ''),
            "message_id": headers.get('message-id', ''),
            "snippet": message.get('snippet', ''),
            "body": body,
            "labels": message.get('labelIds', [])
        }
    
    def _get_body(self, payload: Dict) -> str:
        """Extract text body from message payload."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            # Try nested parts
            for part in payload['parts']:
                body = self._get_body(part)
                if body:
                    return body
        
        return ""
    
    def check_for_job_responses(self, since_hours: int = 24) -> List[Dict]:
        """
        Check for emails that might be job responses.
        """
        # Search for potential job-related emails
        queries = [
            "subject:(application OR interview OR position OR role OR opportunity)",
            "from:(recruiter OR hr OR talent OR career OR hiring)",
            "subject:(thank you for applying OR we received your application)"
        ]
        
        all_messages = []
        for query in queries:
            messages = self.get_messages(query=f"{query} newer_than:{since_hours}h", max_results=5)
            all_messages.extend(messages)
        
        # Dedupe by message ID
        seen = set()
        unique = []
        for msg in all_messages:
            if msg['id'] not in seen:
                seen.add(msg['id'])
                unique.append(msg)
        
        return unique
    
    # ============================================
    # LABEL OPERATIONS
    # ============================================
    
    def get_or_create_label(self, label_name: str) -> str:
        """Get or create a Gmail label."""
        labels = self.service.users().labels().list(userId='me').execute().get('labels', [])
        
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        # Create new label
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        new_label = self.service.users().labels().create(userId='me', body=label_body).execute()
        return new_label['id']
    
    def add_label(self, message_id: str, label_name: str):
        """Add a label to a message."""
        label_id = self.get_or_create_label(label_name)
        self.service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
    
    def mark_as_read(self, message_id: str):
        """Mark message as read."""
        self.service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
