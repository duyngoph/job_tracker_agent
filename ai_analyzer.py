import openai
import json
import re
from typing import Dict, Optional, List
from datetime import datetime

from config import Config


class JobEmailAnalyzer:
    """AI-powered email analyzer for job application tracking"""
    
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.client = openai.OpenAI()
    
    def analyze_email(self, email_data: Dict) -> Dict:
        """Analyze an email to extract job application information"""
        
        prompt = self._create_analysis_prompt(email_data)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant specialized in analyzing job-related emails. 
                        Your task is to extract structured information from emails about job applications, 
                        interviews, rejections, offers, and other job-related communications.
                        
                        Always respond with valid JSON format. Be precise and extract only information 
                        that is clearly stated in the email."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            try:
                    analysis = json.loads(result)
                    analysis = self._validate_and_clean_analysis(analysis)

                    # Apply a confidence threshold to avoid misclassifying social notifications
                    try:
                        threshold = float(Config.JOB_CONFIDENCE_THRESHOLD)
                    except Exception:
                        threshold = 0.6

                    if analysis.get('is_job_related') and analysis.get('confidence_score', 0) < threshold:
                        # downgrade to non-job-related to avoid noisy false positives
                        analysis['is_job_related'] = False

                    # Apply content-based post-processing heuristics (detect offers, interview cues, etc.)
                    analysis = self.postprocess_based_on_content(analysis, email_data)

                    return analysis
            except json.JSONDecodeError:
                print(f"Failed to parse AI response as JSON: {result}")
                return self._create_fallback_analysis(email_data)
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return self._create_fallback_analysis(email_data)
    
    def _create_analysis_prompt(self, email_data: Dict) -> str:
        """Create a detailed prompt for email analysis"""
        
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')
        date = email_data.get('date', '')
        
        prompt = f"""
        Analyze the following job-related email and extract structured information:
        
        EMAIL DETAILS:
        Subject: {subject}
        From: {sender}
        Date: {date}
        
        EMAIL BODY:
        {body[:2000]}  # Limit body to first 2000 characters
        
        Please extract the following information and return it as a JSON object:
        
        {{
            "is_job_related": boolean,
            "email_type": "application_confirmation|interview_invitation|interview_reminder|status_update|rejection|offer|assessment|other",
            "company_name": "string or null",
            "position_title": "string or null",
            "job_status": "Applied|Under Review|Phone Screen|Technical Interview|Final Interview|Offer|Rejected|Withdrawn|null",
            "contact_person": "string or null",
            "contact_email": "string or null",
            "interview_date": "YYYY-MM-DD HH:MM or null",
            "interview_type": "phone|video|in_person|technical|behavioral|null",
            "salary_range": "string or null",
            "location": "string or null",
            "job_url": "string or null",
            "next_steps": "string or null",
            "job_id": "string or null",
            "key_information": "string summary of important details",
            "confidence_score": float between 0 and 1
        }}
        
        Guidelines:
        - Set is_job_related to true only if this is clearly about a job application or career opportunity
        - Extract company name from sender domain or email content
        - Identify position title from subject line or email body
        - Determine current status based on email content
        - Extract any mentioned dates, deadlines, or next steps
        - Provide a confidence score based on how certain you are about the extracted information
        - If information is not clearly stated, use null
        """
        
        return prompt
    
    def _validate_and_clean_analysis(self, analysis: Dict) -> Dict:
        """Validate and clean the AI analysis results"""
        
        # Ensure required fields exist
        required_fields = [
            'is_job_related', 'email_type', 'company_name', 'position_title',
            'job_status', 'contact_person', 'contact_email', 'key_information',
            'confidence_score'
        ]
        
        for field in required_fields:
            if field not in analysis:
                analysis[field] = None
        
        # Validate confidence score
        if not isinstance(analysis.get('confidence_score'), (int, float)):
            analysis['confidence_score'] = 0.5
        else:
            analysis['confidence_score'] = max(0.0, min(1.0, float(analysis['confidence_score'])))
        
        # Validate and normalize job status (case-insensitive mapping to canonical statuses)
        job_status_raw = analysis.get('job_status')
        if job_status_raw:
            try:
                # Build lowercase mapping from canonical statuses
                canonical_map = {s.lower(): s for s in Config.JOB_STATUSES}
                js_lower = str(job_status_raw).strip().lower()
                if js_lower in canonical_map:
                    analysis['job_status'] = canonical_map[js_lower]
                else:
                    # Some models may output phrases like 'offer received' -> map heuristically
                    for key_lower, canon in canonical_map.items():
                        if key_lower in js_lower:
                            analysis['job_status'] = canon
                            break
                    else:
                        analysis['job_status'] = None
            except Exception:
                analysis['job_status'] = None
        else:
            analysis['job_status'] = None
        
        # Clean up string fields
        string_fields = ['company_name', 'position_title', 'contact_person', 'contact_email', 
                        'salary_range', 'location', 'job_url', 'next_steps', 'key_information', 'job_id']
        
        for field in string_fields:
            if analysis.get(field):
                analysis[field] = str(analysis[field]).strip()
                if not analysis[field]:
                    analysis[field] = None

        # Normalize email_type to known tokens (fallback to 'other')
        try:
            allowed_email_types = {
                'application_confirmation', 'interview_invitation', 'interview_reminder',
                'status_update', 'rejection', 'offer', 'assessment', 'other'
            }
            et = analysis.get('email_type')
            if et:
                et_lower = str(et).strip().lower()
                if et_lower in allowed_email_types:
                    analysis['email_type'] = et_lower
                else:
                    # heuristically map common variants
                    if 'offer' in et_lower:
                        analysis['email_type'] = 'offer'
                    elif 'interview' in et_lower:
                        # default to invitation unless 'reminder' present
                        if 'reminder' in et_lower:
                            analysis['email_type'] = 'interview_reminder'
                        else:
                            analysis['email_type'] = 'interview_invitation'
                    elif 'reject' in et_lower or 'rejection' in et_lower:
                        analysis['email_type'] = 'rejection'
                    else:
                        analysis['email_type'] = 'other'
            else:
                analysis['email_type'] = 'other'
        except Exception:
            analysis['email_type'] = analysis.get('email_type') or 'other'

        return analysis
    
    def _create_fallback_analysis(self, email_data: Dict) -> Dict:
        """Create a basic analysis when AI fails"""
        
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        
        # Basic keyword detection
        is_job_related = any(keyword in subject or keyword in body 
                           for keyword in Config.JOB_EMAIL_KEYWORDS)
        
        # Try to extract company from sender domain
        company_name = None
        if '@' in sender:
            domain = sender.split('@')[1].split('>')[0]
            company_name = domain.split('.')[0].title()
        
        return {
            'is_job_related': is_job_related,
            'email_type': 'other',
            'company_name': company_name,
            'position_title': None,
            'job_status': None,
            'contact_person': None,
            'contact_email': sender if '@' in sender else None,
            'interview_date': None,
            'interview_type': None,
            'salary_range': None,
            'location': None,
            'job_url': None,
            'next_steps': None,
            'deadline': None,
            'job_id': None,
            'key_information': f"Email from {sender} with subject: {email_data.get('subject', '')}",
            'confidence_score': 0.3
        }
        """Heuristic to extract job or requisition IDs from text."""
        import re

        if not text:
            return None

        # Common patterns: Job ID: 12345, Requisition #: 6789, Req ID 9876
        patterns = [
            r'job\s*id\s*[:#\-]?\s*(\w+)',
            r'requisition\s*(?:number|#|no\.?|id)\s*[:#\-]?\s*(\w+)',
            r'req\s*#?\s*[:#\-]?\s*(\w+)',
            r'position\s*id\s*[:#\-]?\s*(\w+)',
            r'ref\s*[:#\-]?\s*(\w+)'
        ]

        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)

        # Try to extract IDs from job URLs (e.g., /jobs/12345 or id=12345)
        m = re.search(r'/jobs?/([0-9]+)', text)
        if m:
            return m.group(1)

        m = re.search(r'id=([0-9]+)', text)
        if m:
            return m.group(1)

        return None
    
    def extract_company_from_email(self, email_data: Dict) -> Optional[str]:
        """Extract company name from email sender or content"""
        
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        # Try to extract from sender domain
        if '@' in sender:
            domain = sender.split('@')[1].split('>')[0].lower()
            
            # Skip common recruiting platforms
            recruiting_platforms = ['greenhouse.io', 'lever.co', 'workday.com', 'smartrecruiters.com']
            if not any(platform in domain for platform in recruiting_platforms):
                company_name = domain.split('.')[0]
                return company_name.title()
        
        # Try to extract from subject line patterns
        subject_patterns = [
            r'from\s+([A-Za-z\s]+)',
            r'at\s+([A-Za-z\s]+)',
            r'(\w+)\s+team',
            r'(\w+)\s+hiring'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        
        return None
    
    def determine_email_urgency(self, analysis: Dict) -> str:
        """Determine the urgency level of the email"""
        
        email_type = analysis.get('email_type', '')
        deadline = analysis.get('deadline')
        interview_date = analysis.get('interview_date')
        
        if email_type in ['interview_invitation', 'offer']:
            return 'high'
        elif email_type in ['interview_reminder', 'assessment']:
            return 'medium'
        elif deadline or interview_date:
            return 'medium'
        else:
            return 'low'

    def postprocess_based_on_content(self, analysis: Dict, email_data: Dict) -> Dict:
        """Heuristic post-processing to catch obvious signals missed by the model.

        - Detect offer-related phrases and set job_status/email_type accordingly
        - Boost confidence when content clearly contains offer/interview language
        """
        subject = (email_data.get('subject') or '').lower()
        body = (email_data.get('body') or '').lower()

        # Offer detection
        offer_phrases = [
            'we are pleased to offer', 'congratulations', 'offer of employment',
            'offer letter', 'you have been offered', 'official offer', 'job offer',
            'we would like to offer you'
        ]

        interview_phrases = ['interview', 'schedule', 'availability', 'time to chat', 'invite you to interview']

        # If any offer phrase appears in subject or body, set as Offer
        if any(p in subject or p in body for p in offer_phrases):
            analysis['job_status'] = 'Offer'
            analysis['email_type'] = 'offer'
            # Boost confidence to reflect clear textual evidence
            analysis['confidence_score'] = max(analysis.get('confidence_score', 0.0), 0.9)
            analysis['is_job_related'] = True
            return analysis

        # If interview phrases exist and model didn't mark correctly, nudge it
        if any(p in subject or p in body for p in interview_phrases):
            if 'interview' in analysis.get('email_type', '') or analysis.get('email_type') == 'other':
                analysis['email_type'] = 'interview_invitation'
                analysis['confidence_score'] = max(analysis.get('confidence_score', 0.0), 0.7)
                analysis['is_job_related'] = True

        return analysis
