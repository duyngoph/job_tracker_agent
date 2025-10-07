#!/usr/bin/env python3
"""
Job Application Tracker - Main Entry Point

This script provides a command-line interface for the job application tracking system.
It can run in different modes: one-time check, scheduled monitoring, or interactive mode.
"""

import argparse
import sys
import logging
from datetime import datetime

from job_tracker import JobApplicationTracker
from scheduler import JobTrackerScheduler
from config import validate_config


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('job_tracker.log'),
            logging.StreamHandler()
        ]
    )


def run_one_time_check(hours_back: int = 24):
    """Run a one-time email check"""
    print(f"Running one-time email check for the last {hours_back} hours...")
    
    try:
        tracker = JobApplicationTracker()
        results = tracker.process_recent_emails(hours_back)
        
        print("\n" + "="*50)
        print("EMAIL PROCESSING RESULTS")
        print("="*50)
        print(f"Total emails processed: {results['total_emails']}")
        print(f"Job-related emails found: {results['job_related_emails']}")
        print(f"New applications created: {results['new_applications']}")
        print(f"Existing applications updated: {results['updated_applications']}")
        print(f"Errors encountered: {results['errors']}")
        
        if results['processed_emails']:
            print("\nProcessed Emails:")
            print("-" * 30)
            for email in results['processed_emails']:
                print(f"• {email['subject'][:60]}...")
                print(f"  From: {email['sender']}")
                print(f"  Action: {email['result']['action']}")
                if email['analysis'].get('company_name'):
                    print(f"  Company: {email['analysis']['company_name']}")
                if email['analysis'].get('position_title'):
                    print(f"  Position: {email['analysis']['position_title']}")
                print()
        
        return results
        
    except Exception as e:
        print(f"Error during email check: {e}")
        return None


def run_search_and_process(days_back: int = 7):
    """Search for job-related emails and process them"""
    print(f"Searching for job-related emails from the last {days_back} days...")
    
    try:
        tracker = JobApplicationTracker()
        results = tracker.search_and_process_job_emails(days_back)
        
        print("\n" + "="*50)
        print("EMAIL SEARCH AND PROCESSING RESULTS")
        print("="*50)
        print(f"Total emails found: {results['total_emails']}")
        print(f"Job-related emails: {results['job_related_emails']}")
        print(f"New applications created: {results['new_applications']}")
        print(f"Existing applications updated: {results['updated_applications']}")
        print(f"Errors encountered: {results['errors']}")
        
        return results
        
    except Exception as e:
        print(f"Error during email search: {e}")
        return None


def show_summary():
    """Show application summary"""
    try:
        tracker = JobApplicationTracker()
        summary = tracker.get_application_summary()
        
        print("\n" + "="*50)
        print("JOB APPLICATION SUMMARY")
        print("="*50)
        print(f"Total Applications: {summary['total_applications']}")
        
        print("\nStatus Breakdown:")
        for status, count in summary['status_breakdown'].items():
            print(f"  {status}: {count}")
        
        print(f"\nCompanies Applied To: {len(summary['companies'])}")
        if summary['companies']:
            for company in sorted(summary['companies']):
                print(f"  • {company}")
        
        return summary
        
    except Exception as e:
        print(f"Error getting summary: {e}")
        return None


def run_scheduler():
    """Run the automated scheduler"""
    print("Starting automated job application tracker...")
    print("Press Ctrl+C to stop")
    
    try:
        scheduler = JobTrackerScheduler()
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")
    except Exception as e:
        print(f"Scheduler error: {e}")


def interactive_mode():
    """Run in interactive mode"""
    print("\n" + "="*50)
    print("JOB APPLICATION TRACKER - INTERACTIVE MODE")
    print("="*50)
    
    while True:
        print("\nAvailable commands:")
        print("1. Check recent emails (last 24 hours)")
        print("2. Search job emails (last 7 days)")
        print("3. Show application summary")
        print("4. Start automated scheduler")
        print("5. Custom email check")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            run_one_time_check(24)
        elif choice == '2':
            run_search_and_process(7)
        elif choice == '3':
            show_summary()
        elif choice == '4':
            run_scheduler()
        elif choice == '5':
            try:
                hours = int(input("Enter hours back to check: "))
                run_one_time_check(hours)
            except ValueError:
                print("Invalid number entered")
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Job Application Tracker - Automated email monitoring and spreadsheet updates"
    )
    
    parser.add_argument(
        '--mode', 
        choices=['check', 'search', 'summary', 'schedule', 'interactive'],
        default='interactive',
        help='Operation mode (default: interactive)'
    )
    
    parser.add_argument(
        '--hours-back',
        type=int,
        default=24,
        help='Hours back to check for emails (default: 24)'
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=7,
        help='Days back to search for emails (default: 7)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    print("Job Application Tracker")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run based on mode
    if args.mode == 'check':
        run_one_time_check(args.hours_back)
    elif args.mode == 'search':
        run_search_and_process(args.days_back)
    elif args.mode == 'summary':
        show_summary()
    elif args.mode == 'schedule':
        run_scheduler()
    elif args.mode == 'interactive':
        interactive_mode()


if __name__ == "__main__":
    main()
