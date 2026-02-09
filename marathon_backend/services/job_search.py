"""
Job Search Service - Uses Gemini (now via OpenRouter proxy) to find job listings.
"""
import os
import json
import base64
import time
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timezone
from dotenv import load_dotenv

from .gemini_client import call_gemini

load_dotenv()


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

Search Google for active job listings matching these criteria. Return ONLY valid JSON array with {num_jobs} jobs.
Strictly adhere to this specific JSON structure for each job object:

[
  {{
    "company": "Company Name",
    "job_title": "Exact Job Title",
    "location": "City, Country",
    "job_url": "Direct URL to job posting",
    "salary_range": "e.g. $100k-$120k or 'Competitive' if unknown",
    "posted_date": "e.g. 2 days ago",
    "job_description": "2-3 sentence summary of the role",
    "match_score": 85
  }}
]

IMPORTANT:
- "salary_range" is required (guess based on market if not listed, but prefer actual data).
- "match_score" must be an integer 0-100.
- Return ONLY the JSON array. No markdown formatting or explanation. 
- Ensure valid URLs.
"""

    # Call OpenRouter-proxied Gemini via our helper. We wrap the call so
    # `call_with_retry` can retry on exceptions. `call_gemini` returns a
    # plain string response (or an error string), so we parse JSON from it.
    def _call_gemini_wrapper():
        resp = call_gemini(prompt, max_tokens=4096, temperature=0.3)
        # call_gemini returns error messages as strings; convert them to exceptions
        if isinstance(resp, str) and (resp.startswith("API Error") or resp.startswith("Request Failed") or resp.startswith("Error:")):
            raise Exception(resp)
        return resp

    try:
        response_text = call_with_retry(_call_gemini_wrapper)
    except Exception as e:
        print(f"⚠️ Gemini/OpenRouter call failed: {e}")
        return [], None

    # We don't currently extract a thought signature from OpenRouter responses
    signature = None

    # Parse response text as JSON (strip markdown fences if present)
    try:
        text = response_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) > 1:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        jobs = json.loads(text.strip())
        return jobs, signature
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse jobs JSON: {e}\nRaw response:\n{text}")
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
        Use advanced Google search techniques (site:linkedin.com/jobs OR site:indeed.com , filter by last 7 days, include 'apply' or 'application email' keywords) to find jobs.
        
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
