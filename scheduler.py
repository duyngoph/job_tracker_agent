import schedule
import time
import logging
from datetime import datetime

from job_tracker import JobApplicationTracker
from config import Config


class JobTrackerScheduler:
    """Scheduler for automated job application tracking"""
    
    def __init__(self):
        self.tracker = JobApplicationTracker()
        self.logger = logging.getLogger(__name__)
        self.setup_schedule()
    
    def setup_schedule(self):
        """Setup the automated schedule for email checking"""
        # Schedule regular email checks: prefer seconds if provided
        if getattr(Config, 'CHECK_INTERVAL_SECONDS', 0) and Config.CHECK_INTERVAL_SECONDS > 0:
            schedule.every(Config.CHECK_INTERVAL_SECONDS).seconds.do(self.run_email_check)
            interval_desc = f"{Config.CHECK_INTERVAL_SECONDS} seconds"
        else:
            schedule.every(Config.CHECK_INTERVAL_MINUTES).minutes.do(self.run_email_check)
            interval_desc = f"{Config.CHECK_INTERVAL_MINUTES} minutes"
        
        # Schedule daily summary (optional)
        schedule.every().day.at("09:00").do(self.run_daily_summary)

        self.logger.info(f"Scheduler setup complete. Will check emails every {interval_desc}")
    
    def run_email_check(self):
        """Run the email check process"""
        try:
            self.logger.info("Starting scheduled email check...")
            
            # Process emails from the last interval + buffer
            hours_back = max(1, Config.CHECK_INTERVAL_MINUTES // 60 + 1)
            results = self.tracker.process_recent_emails(hours_back)
            
            self.logger.info(f"Email check completed: {results}")
            
            # Log summary
            if results['job_related_emails'] > 0:
                self.logger.info(
                    f"Found {results['job_related_emails']} job-related emails. "
                    f"Created {results['new_applications']} new applications, "
                    f"updated {results['updated_applications']} existing applications."
                )
            
        except Exception as e:
            self.logger.error(f"Error during scheduled email check: {e}")
    
    def run_daily_summary(self):
        """Run daily summary report"""
        try:
            self.logger.info("Generating daily summary...")
            
            summary = self.tracker.get_application_summary()
            
            self.logger.info(f"Daily Summary - Total Applications: {summary['total_applications']}")
            self.logger.info(f"Status Breakdown: {summary['status_breakdown']}")
            
        except Exception as e:
            self.logger.error(f"Error generating daily summary: {e}")
    
    def run_once(self):
        """Run email check once (for testing or manual execution)"""
        self.logger.info("Running one-time email check...")
        return self.run_email_check()
    
    def start(self):
        """Start the scheduler"""
        self.logger.info("Starting Job Application Tracker Scheduler...")
        
        # Run initial check
        self.run_once()
        
        # Start the scheduler loop
        # Determine wake-up granularity based on whether we use seconds scheduling
        loop_sleep = 1 if getattr(Config, 'CHECK_INTERVAL_SECONDS', 0) and Config.CHECK_INTERVAL_SECONDS > 0 else 60

        while True:
            try:
                schedule.run_pending()
                time.sleep(loop_sleep)
                
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(5 if loop_sleep == 1 else 300)  # short backoff for second-level loop


if __name__ == "__main__":
    scheduler = JobTrackerScheduler()
    scheduler.start()
