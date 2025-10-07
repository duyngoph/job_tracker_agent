import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Job Application Tracker"""
    
    # Gmail API Configuration
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    GMAIL_CREDENTIALS_FILE = 'credentials.json'
    GMAIL_TOKEN_FILE = 'token.json'
    
    # Google Sheets API Configuration
    SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SHEETS_CREDENTIALS_FILE = 'sheets_credentials.json'
    SHEETS_TOKEN_FILE = 'sheets_token.json'
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Google Sheets Configuration
    SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
    WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', 'Job Applications')
    
    # Email Processing Configuration
    # Scheduling: prefer seconds if specified, otherwise use minutes
    CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', 0))
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 30))
    MAX_EMAILS_PER_CHECK = int(os.getenv('MAX_EMAILS_PER_CHECK', 50))
    
    # Job Application Tracking Configuration
    JOB_STATUSES = [
        'Applied',
        'Under Review',
        'Phone Screen',
        'Technical Interview',
        'Final Interview',
        'Offer',
        'Rejected',
        'Withdrawn'
    ]
    
    # Email Classification Keywords
    JOB_EMAIL_KEYWORDS = [
        'application', 'interview', 'position', 'role', 'job', 'career',
        'hiring', 'recruitment', 'recruiter', 'hr', 'human resources',
        'offer', 'rejection', 'declined', 'accepted', 'screening',
        'assessment', 'technical', 'coding challenge', 'next steps'
    ]
    
    COMPANY_DOMAINS = [
        'greenhouse.io', 'lever.co', 'workday.com', 'smartrecruiters.com',
        'bamboohr.com', 'jobvite.com', 'icims.com', 'taleo.net'
    ]

    # Domains to treat as social/notification senders (often noisy)
    SOCIAL_NETWORK_DOMAINS = [
        'linkedin.com', 'linkedinmail.com', 'bounce.linkedin.com', 'facebookmail.com',
        'twitter.com', 'meetup.com'
    ]

    # Sender domains that should generally be ignored for job-related detection
    SENDER_BLACKLIST = SOCIAL_NETWORK_DOMAINS

    # Minimum confidence score from the AI analyzer to accept a message as job-related
    JOB_CONFIDENCE_THRESHOLD = float(os.getenv('JOB_CONFIDENCE_THRESHOLD', 0.6))

# Validate required environment variables
def validate_config():
    """Validate that all required configuration is present"""
    required_vars = ['OPENAI_API_KEY', 'GOOGLE_SPREADSHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
