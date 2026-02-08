"""
Database client and helper functions for Supabase.
"""
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


# ============================================
# PROFILE OPERATIONS
# ============================================

def get_profile(user_id: str) -> Optional[Dict]:
    """Get user profile by ID."""
    res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data if res.data else None


def get_profile_by_name(full_name: str) -> Optional[Dict]:
    """Get user profile by name."""
    res = supabase.table("profiles").select("*").eq("full_name", full_name).execute()
    return res.data[0] if res.data else None


def create_profile(data: Dict) -> Dict:
    """Create a new profile."""
    res = supabase.table("profiles").insert(data).execute()
    return res.data[0] if res.data else None


def update_profile(user_id: str, data: Dict) -> Dict:
    """Update profile fields."""
    res = supabase.table("profiles").update(data).eq("id", user_id).execute()
    return res.data[0] if res.data else None


def get_or_create_profile(full_name: str, default_data: Dict = None) -> Dict:
    """Get existing profile or create new one."""
    existing = get_profile_by_name(full_name)
    if existing:
        return existing
    
    data = default_data or {}
    data["full_name"] = full_name
    return create_profile(data)


# ============================================
# AGENT STATE OPERATIONS
# ============================================

def get_agent_state(user_id: str) -> Optional[Dict]:
    """Get agent state for a user."""
    res = supabase.table("agent_states").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def save_agent_state(user_id: str, state: Dict) -> Dict:
    """Upsert agent state."""
    state["user_id"] = user_id
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    res = supabase.table("agent_states").upsert(state, on_conflict="user_id").execute()
    return res.data[0] if res.data else None


def get_all_active_campaigns() -> List[Dict]:
    """Get all agent states with active campaigns."""
    res = supabase.table("agent_states").select("*, profiles(*)").execute()
    
    active = []
    for agent in res.data:
        history = agent.get("history", [])
        for item in history:
            if isinstance(item, dict) and item.get("type") == "campaign_config":
                if item.get("is_active", False):
                    agent["_config"] = item
                    active.append(agent)
                break
    return active


# ============================================
# JOB APPLICATION OPERATIONS
# ============================================

def create_job_application(user_id: str, job: Dict, status: str = "scouted") -> Dict:
    """Create a new job application."""
    data = {
        "user_id": user_id,
        "job_title": job.get("title"),
        "company_name": job.get("company"),
        "source_url": job.get("url"),
        "location": job.get("location"),
        "posted_date": job.get("posted_date"),
        "match_score": job.get("match_score", 0),
        "job_description": job.get("description"),
        "status": status,
        "replies_log": [{
            "action": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    res = supabase.table("job_applications").insert(data).execute()
    return res.data[0] if res.data else None


def get_job_application(job_id: str) -> Optional[Dict]:
    """Get job application by ID."""
    res = supabase.table("job_applications").select("*").eq("id", job_id).single().execute()
    return res.data if res.data else None


def get_user_applications(user_id: str, status: str = None) -> List[Dict]:
    """Get all job applications for a user, optionally filtered by status."""
    query = supabase.table("job_applications").select("*").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    res = query.order("created_at", desc=True).execute()
    return res.data or []


def update_job_application(job_id: str, data: Dict) -> Dict:
    """Update job application fields."""
    data["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    res = supabase.table("job_applications").update(data).eq("id", job_id).execute()
    return res.data[0] if res.data else None


def get_applied_job_keys(user_id: str) -> set:
    """Get set of company|title keys for deduplication."""
    apps = get_user_applications(user_id)
    return {f"{a['company_name'].lower().strip()}|{a['job_title'].lower().strip()}" for a in apps}


def get_pending_applications(user_id: str) -> List[Dict]:
    """Get scouted jobs that need processing."""
    res = supabase.table("job_applications").select("*").eq("user_id", user_id).eq("status", "scouted").order("created_at", desc=False).execute()
    return res.data or []


# ============================================
# GMAIL TOKEN OPERATIONS
# ============================================

def get_gmail_token(user_id: str) -> Optional[Dict]:
    """Get Gmail OAuth token for user."""
    res = supabase.table("user_gmail_tokens").select("*").eq("user_id", user_id).eq("is_active", True).execute()
    return res.data[0] if res.data else None


def save_gmail_token(user_id: str, email: str, tokens: Dict) -> Dict:
    """Save or update Gmail OAuth token."""
    data = {
        "user_id": user_id,
        "email_address": email,
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_expiry": tokens.get("expiry"),
        "scopes": tokens.get("scopes", []),
        "is_active": True
    }
    res = supabase.table("user_gmail_tokens").upsert(data, on_conflict="user_id").execute()
    return res.data[0] if res.data else None


def delete_gmail_token(user_id: str) -> bool:
    """Deactivate Gmail token."""
    supabase.table("user_gmail_tokens").update({"is_active": False}).eq("user_id", user_id).execute()
    return True


# ============================================
# EMAIL THREAD OPERATIONS
# ============================================

def create_email_thread(user_id: str, thread_data: Dict) -> Dict:
    """Create or update email thread."""
    data = {
        "user_id": user_id,
        "gmail_thread_id": thread_data.get("thread_id"),
        "gmail_message_id": thread_data.get("message_id"),
        "subject": thread_data.get("subject"),
        "last_sender": thread_data.get("sender"),
        "last_snippet": thread_data.get("snippet"),
        "is_job_related": thread_data.get("is_job_related", False),
        "job_application_id": thread_data.get("job_application_id"),
        "status": thread_data.get("status", "pending")
    }
    res = supabase.table("email_threads").upsert(
        data, 
        on_conflict="gmail_thread_id,user_id"
    ).execute()
    return res.data[0] if res.data else None


def get_email_threads(user_id: str, status: str = None) -> List[Dict]:
    """Get email threads for user."""
    query = supabase.table("email_threads").select("*, job_applications(*)").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    res = query.order("updated_at", desc=True).execute()
    return res.data or []


def update_email_thread(thread_id: str, data: Dict) -> Dict:
    """Update email thread."""
    res = supabase.table("email_threads").update(data).eq("id", thread_id).execute()
    return res.data[0] if res.data else None


# ============================================
# CAMPAIGN RUN OPERATIONS
# ============================================

def create_campaign_run(user_id: str, day: int) -> Dict:
    """Create a new campaign run record."""
    res = supabase.table("campaign_runs").insert({
        "user_id": user_id,
        "campaign_day": day,
        "status": "running"
    }).execute()
    return res.data[0] if res.data else None


def update_campaign_run(run_id: str, data: Dict) -> Dict:
    """Update campaign run stats."""
    res = supabase.table("campaign_runs").update(data).eq("id", run_id).execute()
    return res.data[0] if res.data else None


def complete_campaign_run(run_id: str, stats: Dict) -> Dict:
    """Mark campaign run as complete."""
    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["status"] = "completed"
    return update_campaign_run(run_id, stats)


# ============================================
# CLASS WRAPPER FOR ROUTERS
# ============================================

class MarathonDB:
    """Wrapper class for database operations used by routers."""
    
    def __init__(self):
        self.client = supabase
    
    # Profile operations
    def get_profile(self, user_id: str) -> Optional[Dict]:
        return get_profile(user_id)
    
    def create_profile(self, data: Dict) -> Dict:
        return create_profile(data)
    
    def update_profile(self, user_id: str, data: Dict) -> Dict:
        return update_profile(user_id, data)
    
    # Agent state operations
    def get_agent_state(self, state_id: int) -> Optional[Dict]:
        res = supabase.table("agent_states").select("*").eq("id", state_id).single().execute()
        return res.data if res.data else None
    
    def get_agent_states(self, user_id: str) -> List[Dict]:
        res = supabase.table("agent_states").select("*").eq("user_id", user_id).execute()
        return res.data or []
    
    def create_agent_state(self, user_id: str, config: Dict) -> Dict:
        data = {
            "user_id": user_id,
            "config": config,
            "history": [],
            "thought_signature": None
        }
        res = supabase.table("agent_states").insert(data).execute()
        return res.data[0] if res.data else None
    
    def save_agent_state(self, user_id: str, state: Dict) -> Dict:
        return save_agent_state(user_id, state)
    
    # Job applications operations
    def get_job_application(self, job_id: int) -> Optional[Dict]:
        res = supabase.table("job_applications").select("*").eq("id", job_id).single().execute()
        return res.data if res.data else None
    
    def get_user_applications(self, user_id: str, status: str = None) -> List[Dict]:
        return get_user_applications(user_id, status)
    
    def create_job_application(self, user_id: str, job: Dict, status: str = "scouted") -> Dict:
        return create_job_application(user_id, job, status)
    
    def update_job_application(self, job_id: int, data: Dict) -> Dict:
        return update_job_application(str(job_id), data)
    
    # Gmail token operations
    def get_gmail_tokens(self, user_id: str) -> Optional[Dict]:
        token = get_gmail_token(user_id)
        if token:
            return {
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
                "expiry": token.get("token_expiry"),
                "scopes": token.get("scopes", [])
            }
        return None
    
    def save_gmail_tokens(self, user_id: str, email: str, tokens: Dict) -> Dict:
        return save_gmail_token(user_id, email, tokens)
    
    def delete_gmail_tokens(self, user_id: str) -> bool:
        return delete_gmail_token(user_id)
    
    # Campaign run operations
    def create_campaign_run(self, user_id: str, agent_state_id: int, run_type: str = "search") -> Dict:
        res = supabase.table("campaign_runs").insert({
            "user_id": user_id,
            "agent_state_id": agent_state_id,
            "run_type": run_type,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return res.data[0] if res.data else None
    
    def update_campaign_run(self, run_id: int, status: str = None, jobs_found: int = None, 
                           jobs_applied: int = None, summary: str = None) -> Dict:
        data = {}
        if status:
            data["status"] = status
        if jobs_found is not None:
            data["jobs_found"] = jobs_found
        if jobs_applied is not None:
            data["jobs_applied"] = jobs_applied
        if summary:
            data["summary"] = summary
        if status == "completed":
            data["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        res = supabase.table("campaign_runs").update(data).eq("id", run_id).execute()
        return res.data[0] if res.data else None

