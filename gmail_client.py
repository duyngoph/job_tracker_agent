import os
import pickle
import base64
import email
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config


class GmailClient:
    """Gmail API client for reading and processing emails"""
    
    def __init__(self):
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(Config.GMAIL_TOKEN_FILE):
            with open(Config.GMAIL_TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(Config.GMAIL_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {Config.GMAIL_CREDENTIALS_FILE}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GMAIL_CREDENTIALS_FILE, Config.GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(Config.GMAIL_TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def get_recent_emails(self, hours_back: int = 24) -> List[Dict]:
        """Get recent emails from the last specified hours"""
        try:
            # Calculate the date for filtering
            since_date = datetime.now() - timedelta(hours=hours_back)
            query = f'after:{since_date.strftime("%Y/%m/%d")}'
            
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=Config.MAX_EMAILS_PER_CHECK
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = self.get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)

            # Sort emails oldest -> newest before returning so processing is chronological
            emails = self._sort_emails_by_date_asc(emails)
            return emails
            
        except HttpError as error:
            print(f'An error occurred while fetching emails: {error}')
            return []
    
    def get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific email"""
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract header information
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract email body
            body = self.extract_email_body(message['payload'])
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'thread_id': message.get('threadId', ''),
                'labels': message.get('labelIds', [])
            }
            
        except HttpError as error:
            print(f'An error occurred while fetching email {message_id}: {error}')
            return None
    
    def extract_email_body(self, payload: Dict) -> str:
        """Extract the body text from email payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    # You might want to convert HTML to plain text here
                    body = html_body
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/html':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def search_emails_by_keywords(self, keywords: List[str], days_back: int = 7) -> List[Dict]:
        """Search for emails containing specific keywords"""
        try:
            since_date = datetime.now() - timedelta(days=days_back)
            keyword_query = ' OR '.join([f'"{keyword}"' for keyword in keywords])
            query = f'({keyword_query}) after:{since_date.strftime("%Y/%m/%d")}'
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=Config.MAX_EMAILS_PER_CHECK
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = self.get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)

            # Return results sorted from oldest to newest
            emails = self._sort_emails_by_date_asc(emails)
            return emails
        except HttpError as error:
            print(f'An error occurred while searching emails: {error}')
            return []

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse an email Date header into a datetime. Fallback to epoch if parsing fails."""
        if not date_str:
            return datetime.fromtimestamp(0)

        try:
            # parsedate_to_datetime handles most RFC 2822 date formats
            dt = parsedate_to_datetime(date_str)
            # Ensure timezone-aware datetimes are converted to UTC naive or kept consistent
            if dt.tzinfo is not None:
                # convert to UTC and return naive datetime in UTC
                return dt.astimezone(tz=None).replace(tzinfo=None)
            return dt
        except Exception:
            try:
                # Fallback: try ISO parse
                return datetime.fromisoformat(date_str)
            except Exception:
                return datetime.fromtimestamp(0)

    def _sort_emails_by_date_asc(self, emails: List[Dict]) -> List[Dict]:
        """Sort list of email dicts by their 'date' header ascending (oldest first)."""
        try:
            return sorted(emails, key=lambda e: self._parse_email_date(e.get('date', '')))
        except Exception:
            return emails
    
    def is_job_related_email(self, email_data: Dict) -> bool:
        """Basic check to determine if an email is job-related"""
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        
        # Check for job-related keywords
        # If sender is from a known social/notification domain, be conservative:
        sender_domain = self._extract_domain_from_sender(sender)
        if sender_domain in Config.SENDER_BLACKLIST:
            # Only treat as job-related if explicit job keywords or recruiting platforms are present
            if any(keyword in subject or keyword in body for keyword in Config.JOB_EMAIL_KEYWORDS):
                return True
            if any(domain in subject or domain in body for domain in Config.COMPANY_DOMAINS):
                return True
            return False

        # Otherwise, check normal job keywords and recruiting platform domains
        for keyword in Config.JOB_EMAIL_KEYWORDS:
            if keyword in subject or keyword in body:
                return True

        for domain in Config.COMPANY_DOMAINS:
            if domain in sender:
                return True

        return False

    def _extract_domain_from_sender(self, sender: str) -> str:
        """Extract domain from a From header value like 'Name <name@domain.com>'"""
        if '@' in sender:
            try:
                domain = sender.split('@')[1]
                # remove trailing > or additional characters
                domain = domain.split('>')[0].strip().lower()
                # sometimes there's a port or path - keep only domain
                domain = domain.split('/')[0]
                return domain
            except Exception:
                return sender
        return sender
