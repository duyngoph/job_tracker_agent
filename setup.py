#!/usr/bin/env python3
"""
Setup script for Job Application Tracker

This script helps with the initial setup and configuration.
"""

import os
import sys
import json
from pathlib import Path


def create_env_file():
    """Create .env file from template"""
    env_content = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Sheets Configuration
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id_here
WORKSHEET_NAME=Job Applications

# Email Processing Configuration
CHECK_INTERVAL_MINUTES=30
MAX_EMAILS_PER_CHECK=50

# Optional: Custom email filters
# SENDER_WHITELIST=company1.com,company2.com
# SUBJECT_KEYWORDS=application,interview,position
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Created .env file")
        print("  Please edit .env file with your actual API keys and configuration")
    else:
        print("✓ .env file already exists")


def check_credentials_files():
    """Check for required credential files"""
    required_files = [
        ('credentials.json', 'Gmail API credentials'),
        ('sheets_credentials.json', 'Google Sheets API credentials (can be same as Gmail)')
    ]
    
    missing_files = []
    
    for filename, description in required_files:
        if os.path.exists(filename):
            print(f"✓ Found {filename}")
        else:
            print(f"✗ Missing {filename} ({description})")
            missing_files.append((filename, description))
    
    if missing_files:
        print("\nTo get credential files:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Gmail API and Google Sheets API")
        print("4. Create OAuth 2.0 credentials for desktop application")
        print("5. Download and save as credentials.json and sheets_credentials.json")
        return False
    
    return True


def test_imports():
    """Test if all required packages are installed"""
    required_packages = [
        'google.auth',
        'google.oauth2',
        'googleapiclient',
        'openai',
        'schedule',
        'pandas',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('_', '-'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def validate_env_file():
    """Validate .env file configuration"""
    if not os.path.exists('.env'):
        print("✗ .env file not found")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['OPENAI_API_KEY', 'GOOGLE_SPREADSHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
            print(f"✗ {var} not configured")
        else:
            print(f"✓ {var} configured")
    
    if missing_vars:
        print(f"\nPlease configure these variables in .env file: {', '.join(missing_vars)}")
        return False
    
    return True


def create_test_spreadsheet_template():
    """Create a template for the Google Sheets structure"""
    template = {
        "instructions": "Create a Google Sheets document with these column headers in row 1:",
        "headers": [
            "Company",
            "Position", 
            "Status",
            "Date Applied",
            "Last Updated",
            "Contact Person",
            "Contact Email",
            "Job URL",
            "Salary Range",
            "Location",
            "Notes",
            "Email Thread ID"
        ],
        "sample_data": {
            "Company": "Example Corp",
            "Position": "Software Engineer",
            "Status": "Applied",
            "Date Applied": "2024-01-15",
            "Last Updated": "2024-01-15 10:30",
            "Contact Person": "Jane Smith",
            "Contact Email": "jane.smith@example.com",
            "Job URL": "https://example.com/jobs/123",
            "Salary Range": "$80,000 - $120,000",
            "Location": "Remote",
            "Notes": "Applied through company website",
            "Email Thread ID": ""
        }
    }
    
    with open('spreadsheet_template.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print("✓ Created spreadsheet_template.json")
    print("  Use this as a reference for setting up your Google Sheets")


def main():
    """Main setup function"""
    print("Job Application Tracker - Setup Script")
    print("=" * 50)
    
    print("\n1. Checking Python packages...")
    packages_ok = test_imports()
    
    print("\n2. Setting up configuration...")
    create_env_file()
    
    print("\n3. Checking credential files...")
    creds_ok = check_credentials_files()
    
    print("\n4. Creating spreadsheet template...")
    create_test_spreadsheet_template()
    
    print("\n5. Validating configuration...")
    config_ok = validate_env_file()
    
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    if packages_ok and creds_ok and config_ok:
        print("✓ Setup complete! You can now run the job tracker:")
        print("  python main.py")
    else:
        print("✗ Setup incomplete. Please address the issues above.")
        
        if not packages_ok:
            print("  - Install required packages: pip install -r requirements.txt")
        if not creds_ok:
            print("  - Download Google API credential files")
        if not config_ok:
            print("  - Configure .env file with your API keys")
    
    print("\nFor detailed instructions, see README.md")


if __name__ == "__main__":
    main()
