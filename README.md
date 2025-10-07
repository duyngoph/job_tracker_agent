# Job Application Tracker
# Author: Tom Ngo
An AI-powered system that automatically monitors your Gmail inbox for job-related emails and updates your Google Sheets job application tracker.

## Features

- **Automated Email Monitoring**: Continuously monitors your Gmail for job-related emails
- **AI-Powered Analysis**: Uses OpenAI GPT-4 to analyze and extract job application information
- **Google Sheets Integration**: Automatically updates your job tracking spreadsheet
- **Smart Classification**: Identifies application confirmations, interview invitations, rejections, offers, and more
- **Duplicate Detection**: Prevents duplicate entries by matching companies and positions
- **Flexible Scheduling**: Run on-demand or set up automated monitoring

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Gmail account with API access
- Google Sheets document for tracking applications
- OpenAI API key

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Google API Setup

#### Gmail API Setup:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create credentials (OAuth 2.0 Client ID) for a desktop application
5. Download the credentials file and save it as `credentials.json` in the project directory

#### Google Sheets API Setup:
1. In the same Google Cloud project, enable the Google Sheets API
2. Create credentials for the Sheets API (you can use the same OAuth client)
3. Save the credentials file as `sheets_credentials.json`

### 4. Create Your Job Tracking Spreadsheet

1. Create a new Google Sheets document
2. Copy the spreadsheet ID from the URL (the long string between `/d/` and `/edit`)
3. The system will automatically create headers in the first row

### 5. Environment Configuration

1. Copy `env_example.txt` to `.env`
2. Fill in your configuration:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Sheets Configuration
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id_here
WORKSHEET_NAME=Job Applications

# Email Processing Configuration
CHECK_INTERVAL_MINUTES=30
MAX_EMAILS_PER_CHECK=50
```

### 6. First Run Authorization

On the first run, the system will open a browser window for you to authorize access to your Gmail and Google Sheets. This creates token files that are used for subsequent runs.

## Usage

### Interactive Mode (Recommended for first-time users)

```bash
python main.py
```

This opens an interactive menu where you can:
- Check recent emails
- Search for job-related emails
- View application summary
- Start automated monitoring

### Command Line Options

```bash
# Check emails from the last 24 hours
python main.py --mode check

# Search for job emails from the last 7 days
python main.py --mode search --days-back 7

# Show application summary
python main.py --mode summary

# Start automated scheduler
python main.py --mode schedule

# Custom time range
python main.py --mode check --hours-back 48
```

### Automated Monitoring

```bash
# Start continuous monitoring (checks every 30 minutes by default, you can change this value by visiting the .env file and insert the line CHECK_INTERVAL_SECONDS)
python main.py --mode schedule
```

## How It Works

1. **Email Retrieval**: The system connects to your Gmail account and retrieves recent emails
2. **Initial Filtering**: Emails are filtered for job-related keywords and sender domains
3. **AI Analysis**: OpenAI GPT-4 analyzes each email to extract:
   - Company name
   - Position title
   - Application status
   - Contact information
   - Interview details
   - Important dates and deadlines
4. **Spreadsheet Updates**: 
   - New applications are added as new rows
   - Existing applications are updated with new information
   - Status changes are tracked with timestamps

## Spreadsheet Columns

The system creates and manages these columns in your Google Sheets:

- **Company**: Company name
- **Position**: Job title/position
- **Status**: Current application status (Applied, Under Review, Interview, etc.)
- **Date Applied**: When you applied
- **Last Updated**: When the record was last modified
- **Contact Person**: Recruiter or hiring manager name
- **Contact Email**: Contact email address
- **Job URL**: Link to job posting
- **Salary Range**: Salary information if mentioned
- **Location**: Job location
- **Notes**: Detailed notes and timeline
- **Email Thread ID**: Internal tracking for email threads

## Email Types Detected

- Application confirmations
- Interview invitations
- Interview reminders
- Status updates
- Rejection notifications
- Job offers
- Assessment/coding challenge invitations
- General correspondence

## Configuration Options

### Email Processing
- `CHECK_INTERVAL_MINUTES`: How often to check for new emails (default: 30)
- `MAX_EMAILS_PER_CHECK`: Maximum emails to process per check (default: 50)

### Customization
- Add company domains to `COMPANY_DOMAINS` in `config.py`
- Modify job-related keywords in `JOB_EMAIL_KEYWORDS`
- Adjust job statuses in `JOB_STATUSES`

## Troubleshooting

### Common Issues

1. **Authentication Errors**: 
   - Ensure credentials files are in the correct location
   - Check that APIs are enabled in Google Cloud Console
   - Verify OAuth consent screen is configured

2. **OpenAI API Errors**:
   - Verify your API key is correct
   - Check your OpenAI account has sufficient credits
   - Ensure you have access to GPT-4

3. **Spreadsheet Access**:
   - Verify the spreadsheet ID is correct
   - Ensure the spreadsheet is accessible with your Google account
   - Check that the Sheets API is enabled

4. **No Emails Found**:
   - Check your email filters and keywords
   - Verify the time range is appropriate
   - Look at the log files for detailed information

### Logs

The system creates detailed logs in `job_tracker.log`. Check this file for debugging information.

## Security Notes

- API credentials are stored locally and not transmitted
- The system only reads emails (no modification or deletion)
- All data processing happens locally except for OpenAI API calls
- Consider using application-specific passwords for Gmail if you have 2FA enabled

## Limitations

- Requires internet connection for API calls
- OpenAI API usage costs apply (typically $0.01-0.10 per email analysis)
- Gmail API has daily quotas (usually sufficient for personal use)
- May require periodic re-authorization (tokens expire)

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for personal use. Please respect API terms of service for Gmail, Google Sheets, and OpenAI.