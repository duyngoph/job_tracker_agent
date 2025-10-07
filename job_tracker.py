import logging
from datetime import datetime
from typing import List, Dict, Optional

from gmail_client import GmailClient
from sheets_client import SheetsClient
from ai_analyzer import JobEmailAnalyzer
from config import Config, validate_config


class JobApplicationTracker:
    """Main class for tracking job applications via email analysis"""
    
    def __init__(self):
        # Validate configuration
        validate_config()
        
        # Initialize clients
        self.gmail_client = GmailClient()
        self.sheets_client = SheetsClient()
        self.ai_analyzer = JobEmailAnalyzer()
        
        # Setup logging
        self.setup_logging()
        
        self.logger.info("Job Application Tracker initialized successfully")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('job_tracker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def process_recent_emails(self, hours_back: int = 24) -> Dict:
        """Process recent emails for job application updates"""
        
        self.logger.info(f"Processing emails from the last {hours_back} hours")
        
        # Get recent emails
        emails = self.gmail_client.get_recent_emails(hours_back)
        
        results = {
            'total_emails': len(emails),
            'job_related_emails': 0,
            'new_applications': 0,
            'updated_applications': 0,
            'errors': 0,
            'processed_emails': []
        }
        
        for email in emails:
            try:
                # Quick filter for job-related emails
                if not self.gmail_client.is_job_related_email(email):
                    continue
                
                # Analyze email with AI
                analysis = self.ai_analyzer.analyze_email(email)
                
                if not analysis.get('is_job_related', False):
                    continue
                
                results['job_related_emails'] += 1
                
                # Process the analyzed email
                processing_result = self.process_analyzed_email(email, analysis)
                
                if processing_result['action'] == 'new_application':
                    results['new_applications'] += 1
                elif processing_result['action'] == 'updated_application':
                    results['updated_applications'] += 1
                
                results['processed_emails'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', ''),
                    'analysis': analysis,
                    'result': processing_result
                })
                
                self.logger.info(f"Processed email: {email.get('subject', '')[:50]}...")
                
            except Exception as e:
                self.logger.error(f"Error processing email {email.get('id', '')}: {e}")
                results['errors'] += 1
        
        self.logger.info(f"Processing complete. Results: {results}")
        return results
    
    def process_analyzed_email(self, email: Dict, analysis: Dict) -> Dict:
        """Process an email that has been analyzed by AI"""
        
        company = analysis.get('company_name')
        position = analysis.get('position_title')
        thread_id = email.get('thread_id', '')
        job_id = analysis.get('job_id')
        
        if not company:
            company = self.ai_analyzer.extract_company_from_email(email)
        
        # Try to find existing application
        existing_app = None

        # 1) If we extracted a job_id, use it first (most authoritative)
        if job_id:
            existing_app = self.sheets_client.find_application_by_job_id(job_id)

        # 2) If not found, try to find by thread ID
        if not existing_app and thread_id:
            existing_app = self.sheets_client.find_application_by_thread_id(thread_id)

        # 3) If still not found and we have company/position, try that
        if not existing_app and company and position:
            existing_app = self.sheets_client.find_application_by_company_position(company, position)
        
        if existing_app:
            # Update existing application
            return self.update_existing_application(existing_app, email, analysis)
        else:
            # Create new application
            return self.create_new_application(email, analysis)
    
    def create_new_application(self, email: Dict, analysis: Dict) -> Dict:
        """Create a new job application entry"""
        
        company = analysis.get('company_name') or self.ai_analyzer.extract_company_from_email(email)
        position = analysis.get('position_title') or 'Unknown Position'
        
        if not company:
            return {
                'action': 'skipped',
                'reason': 'Could not determine company name'
            }
        
        application_data = {
            'company': company,
            'position': position,
            'status': analysis.get('job_status', 'Applied'),
            'date_applied': datetime.now().strftime('%Y-%m-%d'),
            'contact_person': analysis.get('contact_person'),
            'contact_email': analysis.get('contact_email') or email.get('sender'),
            'job_url': analysis.get('job_url'),
            'salary_range': analysis.get('salary_range'),
            'location': analysis.get('location'),
            'notes': self.create_notes_from_analysis(email, analysis),
            'thread_id': email.get('thread_id', '')
        }
        
        success = self.sheets_client.add_new_application(application_data)
        
        if success:
            self.logger.info(f"Created new application: {company} - {position}")
            return {
                'action': 'new_application',
                'company': company,
                'position': position,
                'status': application_data['status']
            }
        else:
            return {
                'action': 'error',
                'reason': 'Failed to create new application'
            }
    
    def update_existing_application(self, existing_app: Dict, email: Dict, analysis: Dict) -> Dict:
        """Update an existing job application"""
        
        updates = {}
        
        # Update status if provided and different
        new_status = analysis.get('job_status')
        if new_status and new_status != existing_app.get('Status'):
            updates['status'] = new_status
        
        # Update contact information if provided
        if analysis.get('contact_person') and not existing_app.get('Contact Person'):
            updates['contact_person'] = analysis.get('contact_person')
        
        if analysis.get('contact_email') and not existing_app.get('Contact Email'):
            updates['contact_email'] = analysis.get('contact_email')
        
        # Update other fields if missing
        if analysis.get('salary_range') and not existing_app.get('Salary Range'):
            updates['salary_range'] = analysis.get('salary_range')
        
        if analysis.get('location') and not existing_app.get('Location'):
            updates['location'] = analysis.get('location')
        
        # Always update notes with new information
        new_notes = self.create_notes_from_analysis(email, analysis)
        existing_notes = existing_app.get('Notes', '')
        updates['notes'] = f"{existing_notes} | {new_notes}".strip(' |')
        
        # Update thread ID if not present
        if not existing_app.get('Email Thread ID') and email.get('thread_id'):
            updates['thread_id'] = email.get('thread_id')
        
        if updates:
            success = self.sheets_client.update_application(
                existing_app['row_number'], 
                updates
            )
            
            if success:
                self.logger.info(f"Updated application: {existing_app.get('Company')} - {existing_app.get('Position')}")
                return {
                    'action': 'updated_application',
                    'company': existing_app.get('Company'),
                    'position': existing_app.get('Position'),
                    'updates': list(updates.keys())
                }
            else:
                return {
                    'action': 'error',
                    'reason': 'Failed to update application'
                }
        else:
            return {
                'action': 'no_changes',
                'reason': 'No new information to update'
            }
    
    def create_notes_from_analysis(self, email: Dict, analysis: Dict) -> str:
        """Create notes string from email and analysis"""
        
        notes_parts = []
        
        # Add email date and type
        email_date = email.get('date', datetime.now().strftime('%Y-%m-%d'))
        email_type = analysis.get('email_type', 'other')
        notes_parts.append(f"[{email_date}] {email_type.replace('_', ' ').title()}")
        
        # Add key information
        key_info = analysis.get('key_information')
        if key_info:
            notes_parts.append(key_info)
        
        # Add next steps if available
        next_steps = analysis.get('next_steps')
        if next_steps:
            notes_parts.append(f"Next steps: {next_steps}")
        
        # Add interview information
        interview_date = analysis.get('interview_date')
        interview_type = analysis.get('interview_type')
        if interview_date:
            interview_info = f"Interview: {interview_date}"
            if interview_type:
                interview_info += f" ({interview_type})"
            notes_parts.append(interview_info)
        
        # Add deadline if available
        deadline = analysis.get('deadline')
        if deadline:
            notes_parts.append(f"Deadline: {deadline}")
        
        return ' | '.join(notes_parts)
    
    def search_and_process_job_emails(self, days_back: int = 7) -> Dict:
        """Search for job-related emails and process them"""
        
        self.logger.info(f"Searching for job-related emails from the last {days_back} days")
        
        # Search for emails with job-related keywords
        emails = self.gmail_client.search_emails_by_keywords(
            Config.JOB_EMAIL_KEYWORDS, 
            days_back
        )
        
        results = {
            'total_emails': len(emails),
            'job_related_emails': 0,
            'new_applications': 0,
            'updated_applications': 0,
            'errors': 0,
            'processed_emails': []
        }
        
        for email in emails:
            try:
                # Analyze email with AI
                analysis = self.ai_analyzer.analyze_email(email)
                
                if not analysis.get('is_job_related', False):
                    continue
                
                results['job_related_emails'] += 1
                
                # Process the analyzed email
                processing_result = self.process_analyzed_email(email, analysis)
                
                if processing_result['action'] == 'new_application':
                    results['new_applications'] += 1
                elif processing_result['action'] == 'updated_application':
                    results['updated_applications'] += 1
                
                results['processed_emails'].append({
                    'subject': email.get('subject', ''),
                    'sender': email.get('sender', ''),
                    'analysis': analysis,
                    'result': processing_result
                })
                
            except Exception as e:
                self.logger.error(f"Error processing email {email.get('id', '')}: {e}")
                results['errors'] += 1
        
        self.logger.info(f"Search and process complete. Results: {results}")
        return results
    
    def get_application_summary(self) -> Dict:
        """Get a summary of all job applications"""
        
        applications = self.sheets_client.get_all_applications()
        
        summary = {
            'total_applications': len(applications),
            'status_breakdown': {},
            'recent_activity': [],
            'companies': set()
        }
        
        for app in applications:
            status = app.get('Status', 'Unknown')
            summary['status_breakdown'][status] = summary['status_breakdown'].get(status, 0) + 1
            summary['companies'].add(app.get('Company', ''))
        
        summary['companies'] = list(summary['companies'])
        
        return summary
