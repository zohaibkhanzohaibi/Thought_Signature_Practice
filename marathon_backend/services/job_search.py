"""
Job Search Service - Uses Gemini with Google Search grounding.
"""
import os
import json
import base64
import time
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timezone
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"


# ============================================
# RATE LIMIT HANDLING
# ============================================

class DailyLimitReached(Exception):
    """Exception raised when daily API quota is exhausted."""
    def __init__(self, message="Daily API limit reached"):
        self.message = message
        super().__init__(self.message)


def is_rate_limit_error(error) -> Tuple[bool, bool]:
    """
    Detect if error is a rate limit.
    Returns: (is_rate_limit, is_daily_limit)
    """
    error_str = str(error).lower()
    
    if "daily limit" in error_str or "quota exceeded" in error_str:
        return True, True
    if "429" in error_str or "resource_exhausted" in error_str:
        return True, False
    if "503" in error_str or "unavailable" in error_str or "overloaded" in error_str:
        return True, False
    
    return False, False


def call_with_retry(api_func, max_retries=3, wait_seconds=60):
    """
    Call API function with retry logic for rate limits.
    """
    for attempt in range(max_retries + 1):
        try:
            return api_func()
        except Exception as e:
            is_rate_limit, is_daily = is_rate_limit_error(e)
            
            if is_daily:
                print(f"\n🚫 Daily API limit reached!")
                raise DailyLimitReached()
            
            if is_rate_limit and attempt < max_retries:
                print(f"\n⏳ Rate limit hit. Waiting {wait_seconds}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_seconds)
                continue
            
            if is_rate_limit:
                print(f"\n🚫 Rate limit persisted after {max_retries} retries.")
                raise DailyLimitReached()
            
            raise


# ============================================
# SIGNATURE ENCODING
# ============================================

def encode_signature(sig) -> Optional[str]:
    """Encode signature bytes to base64 string."""
    if sig and isinstance(sig, bytes):
        return base64.b64encode(sig).decode('utf-8')
    return sig


def decode_signature(sig_b64) -> Optional[bytes]:
    """Decode base64 string to signature bytes."""
    if sig_b64 and isinstance(sig_b64, str):
        return base64.b64decode(sig_b64)
    return sig_b64


# ============================================
# JOB SEARCH
# ============================================

def search_jobs_with_ai(
    query: str, 
    profile: Dict, 
    location: str,
    exclude_jobs: List[Dict] = None,
    num_jobs: int = 5
) -> Tuple[List[Dict], Optional[bytes]]:
    """
    Use Gemini with Google Search grounding to find real job listings.
    
    Returns: (list of jobs, thought_signature)
    """
    exclude_text = ""
    if exclude_jobs:
        exclude_list = [f"- {j.get('job_title', j.get('title'))} at {j.get('company_name', j.get('company'))}" 
                       for j in exclude_jobs[:20]]
        exclude_text = f"""
IMPORTANT: Do NOT include these jobs (already applied):
{chr(10).join(exclude_list)}
"""

    prompt = f"""You are a job search assistant. Search for REAL, currently open {query} jobs.

USER PROFILE:
- Name: {profile.get('full_name')}
- Skills: {', '.join(profile.get('skills', []))}
- Experience: {profile.get('experience_years', 0)} years
- Location preference: {location}

{exclude_text}

Search Google for active job listings matching these criteria. Return ONLY valid JSON array with {num_jobs} jobs:

[
  {{
    "title": "Exact Job Title from listing",
    "company": "Company Name",
    "location": "City, Country or Remote",
    "url": "Actual job posting URL",
    "match_score": 85,
    "description": "Brief 1-2 sentence description",
    "posted_date": "Today/Yesterday/2 days ago/etc"
  }}
]

IMPORTANT:
- Return REAL jobs from actual job boards (LinkedIn, Indeed, Glassdoor, company sites)
- Include actual URLs that work
- posted_date should be relative (Today, Yesterday, 3 days ago)
- match_score 0-100 based on profile fit
- Focus on {location} or Remote positions
"""

    response = call_with_retry(lambda: client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    ))
    
    # Extract thought signature
    signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            signature = last_part.thought_signature
    
    # Parse response
    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        jobs = json.loads(text.strip())
        return jobs, signature
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse jobs JSON: {e}")
        return [], signature


def get_job_key(job: Dict) -> str:
    """Generate unique key for job deduplication."""
    company = job.get('company', job.get('company_name', '')).lower().strip()
    title = job.get('title', job.get('job_title', '')).lower().strip()
    return f"{company}|{title}"


def filter_duplicate_jobs(jobs: List[Dict], existing_keys: set) -> List[Dict]:
    """Filter out jobs that already exist."""
    new_jobs = []
    for job in jobs:
        key = get_job_key(job)
        if key not in existing_keys:
            new_jobs.append(job)
    return new_jobs


# ============================================
# JOB SEARCH AGENT CLASS
# ============================================

class JobSearchAgent:
    """
    Job Search Agent that wraps AI-powered job search functionality.
    Provides a class-based interface for job searching with profile context.
    """
    
    def __init__(self, profile: Dict = None):
        """Initialize the job search agent with optional profile."""
        self.profile = profile or {}
        self.searched_jobs: List[Dict] = []
        self.last_signature: Optional[bytes] = None
    
    def set_profile(self, profile: Dict):
        """Set or update the user profile."""
        self.profile = profile
    
    def search(
        self, 
        query: str, 
        location: str = "Remote",
        num_jobs: int = 5,
        exclude_applied: bool = True
    ) -> List[Dict]:
        """
        Search for jobs matching the query and profile.
        
        Args:
            query: Job search query (e.g., "Python Developer")
            location: Location preference
            num_jobs: Number of jobs to return
            exclude_applied: Whether to exclude already searched jobs
            
        Returns:
            List of job dictionaries
        """
        exclude_jobs = self.searched_jobs if exclude_applied else None
        
        jobs, signature = search_jobs_with_ai(
            query=query,
            profile=self.profile,
            location=location,
            exclude_jobs=exclude_jobs,
            num_jobs=num_jobs
        )
        
        # Store signature and add to searched jobs
        self.last_signature = signature
        self.searched_jobs.extend(jobs)
        
        return jobs
    
    def get_last_signature(self) -> Optional[bytes]:
        """Get the thought signature from the last search."""
        return self.last_signature
    
    def get_encoded_signature(self) -> Optional[str]:
        """Get the last signature as base64 encoded string."""
        return encode_signature(self.last_signature)
    
    def clear_history(self):
        """Clear the searched jobs history."""
        self.searched_jobs = []
        self.last_signature = None
    
    def get_unique_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs to only return unique ones not in history."""
        existing_keys = {get_job_key(j) for j in self.searched_jobs}
        return filter_duplicate_jobs(jobs, existing_keys)
