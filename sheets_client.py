import os
import pickle
from datetime import datetime
from typing import List, Dict, Optional, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config


class SheetsClient:
    """Google Sheets API client for managing job application data"""
    
    def __init__(self):
        self.service = None
        self.spreadsheet_id = Config.SPREADSHEET_ID
        self.worksheet_name = Config.WORKSHEET_NAME
        self.authenticate()
        self.setup_headers()
    
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(Config.SHEETS_TOKEN_FILE):
            with open(Config.SHEETS_TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(Config.SHEETS_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Sheets credentials file not found: {Config.SHEETS_CREDENTIALS_FILE}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.SHEETS_CREDENTIALS_FILE, Config.SHEETS_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(Config.SHEETS_TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('sheets', 'v4', credentials=creds)
    
    def setup_headers(self):
        """Setup the header row if it doesn't exist"""
        headers = [
            'Company',
            'Position',
            'Job ID',
            'Status',
            'Date Applied',
            'Last Updated',
            'Contact Person',
            'Contact Email',
            'Job URL',
            'Salary Range',
            'Location',
            'Notes',
            'Email Thread ID'
        ]
        
        try:
            # Ensure worksheet exists and safely quote the name for ranges
            safe_name = self._quote_sheet_name(self.worksheet_name)

            # Check if headers already exist (A1:M1 now includes Job ID)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{safe_name}!A1:M1"
            ).execute()

            values = result.get('values', [])

            # If no headers exist, create them
            if not values:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{safe_name}!A1:M1",
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
                print("Headers created in spreadsheet")

        except HttpError as error:
            # If the worksheet/tab doesn't exist, try to create it and retry header setup
            err_str = str(error)
            print(f'An error occurred while setting up headers: {error}')

            try:
                # Create sheet/tab if missing
                if 'Unable to parse range' in err_str or 'Requested entity was not found' in err_str:
                    self._ensure_worksheet_exists(self.worksheet_name)
                    # Retry header creation once
                    safe_name = self._quote_sheet_name(self.worksheet_name)
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{safe_name}!A1:L1",
                        valueInputOption='RAW',
                        body={'values': [headers]}
                    ).execute()
                    print("Headers created in spreadsheet after creating worksheet/tab")

            except HttpError as e2:
                print(f'Failed to create worksheet or write headers: {e2}')


    def _quote_sheet_name(self, name: str) -> str:
        """Return a safely quoted worksheet name for use in A1 ranges.

        Google Sheets requires single quotes around sheet names that contain spaces or special characters.
        Any single quote in the sheet name must be escaped by doubling it.
        Example: O'Neil -> 'O''Neil'
        """
        if not name:
            return "'Sheet1'"

        escaped = name.replace("'", "''")
        return f"'{escaped}'"


    def _ensure_worksheet_exists(self, name: str):
        """Create a new worksheet/tab with the given name if it doesn't exist."""
        try:
            # Get spreadsheet metadata
            meta = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = meta.get('sheets', [])
            for s in sheets:
                props = s.get('properties', {})
                if props.get('title') == name:
                    return  # already exists

            # Add sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': name
                    }
                }
            }]

            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()

        except HttpError as e:
            print(f'Error ensuring worksheet exists: {e}')
    
    def get_all_applications(self) -> List[Dict]:
        """Get all job applications from the spreadsheet"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self._quote_sheet_name(self.worksheet_name)}!A:M"
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return []
            
            headers = values[0]
            applications = []
            
            for i, row in enumerate(values[1:], start=2):
                # Pad row with empty strings if it's shorter than headers
                padded_row = row + [''] * (len(headers) - len(row))
                
                app_data = dict(zip(headers, padded_row))
                app_data['row_number'] = i
                applications.append(app_data)
            
            return applications
            
        except HttpError as error:
            print(f'An error occurred while getting applications: {error}')
            return []
    
    def find_application_by_company_position(self, company: str, position: str) -> Optional[Dict]:
        """Find an existing application by company and position"""
        applications = self.get_all_applications()
        
        for app in applications:
            if (app.get('Company', '').lower() == company.lower() and 
                app.get('Position', '').lower() == position.lower()):
                return app
        
        return None
    
    def find_application_by_thread_id(self, thread_id: str) -> Optional[Dict]:
        """Find an existing application by email thread ID"""
        applications = self.get_all_applications()
        
        for app in applications:
            if app.get('Email Thread ID', '') == thread_id:
                return app
        
        return None

    def find_application_by_job_id(self, job_id: str) -> Optional[Dict]:
        """Find an existing application by Job ID"""
        if not job_id:
            return None

        applications = self.get_all_applications()
        for app in applications:
            if str(app.get('Job ID', '')).strip() == str(job_id).strip():
                return app

        return None
    
    def add_new_application(self, application_data: Dict) -> bool:
        """Add a new job application to the spreadsheet"""
        try:
            # Prepare the row data
            row_data = [
                application_data.get('company', ''),
                application_data.get('position', ''),
                application_data.get('job_id', ''),
                application_data.get('status', 'Applied'),
                application_data.get('date_applied', datetime.now().strftime('%Y-%m-%d')),
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                application_data.get('contact_person', ''),
                application_data.get('contact_email', ''),
                application_data.get('job_url', ''),
                application_data.get('salary_range', ''),
                application_data.get('location', ''),
                application_data.get('notes', ''),
                application_data.get('thread_id', '')
            ]
            
            # Find the next empty row
            applications = self.get_all_applications()
            next_row = len(applications) + 2  # +2 because of header row and 1-based indexing
            
            # Add the new row
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self._quote_sheet_name(self.worksheet_name)}!A{next_row}:M{next_row}",
                valueInputOption='RAW',
                body={'values': [row_data]}
            ).execute()
            
            print(f"Added new application: {application_data.get('company')} - {application_data.get('position')}")
            return True
            
        except HttpError as error:
            print(f'An error occurred while adding application: {error}')
            return False
    
    def update_application(self, row_number: int, updates: Dict) -> bool:
        """Update an existing application"""
        try:
            # Get current row data
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self._quote_sheet_name(self.worksheet_name)}!A{row_number}:M{row_number}"
            ).execute()
            
            current_row = result.get('values', [[]])[0]
            
            # Pad with empty strings if needed
            while len(current_row) < 13:
                current_row.append('')
            
            # Update specific fields
            field_mapping = {
                'company': 0,
                'position': 1,
                'job_id': 2,
                'status': 3,
                'date_applied': 4,
                'last_updated': 5,
                'contact_person': 6,
                'contact_email': 7,
                'job_url': 8,
                'salary_range': 9,
                'location': 10,
                'notes': 11,
                'thread_id': 12
            }
            
            for field, value in updates.items():
                if field in field_mapping:
                    current_row[field_mapping[field]] = value
            
            # Always update the last_updated field
            current_row[5] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Update the row
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self._quote_sheet_name(self.worksheet_name)}!A{row_number}:M{row_number}",
                valueInputOption='RAW',
                body={'values': [current_row]}
            ).execute()
            
            print(f"Updated application in row {row_number}")
            return True
            
        except HttpError as error:
            print(f'An error occurred while updating application: {error}')
            return False
    
    def update_application_status(self, company: str, position: str, new_status: str, notes: str = '') -> bool:
        """Update the status of an existing application"""
        application = self.find_application_by_company_position(company, position)
        
        if application:
            updates = {
                'status': new_status,
                'notes': f"{application.get('Notes', '')} | {notes}".strip(' |')
            }
            return self.update_application(application['row_number'], updates)
        else:
            print(f"Application not found: {company} - {position}")
            return False
