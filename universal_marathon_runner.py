"""
universal_marathon_runner.py - Multi-User Campaign Processor

This script runs as a background job (via GitHub Actions or Cron) and processes
ALL active user campaigns. It uses the job_applications table to track applications.

Schema Used:
- profiles: User profiles with contact info
- agent_states: Stores thought_signature, history, and campaign state in history JSON
- job_applications: Tracks job applications with status (scouted, applied, etc.)
"""

import os
import json
from datetime import date, datetime
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Setup Clients
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

MODEL_ID = "gemini-2.0-flash-thinking-exp"


def get_or_create_profile(full_name: str, email: str = None, summary: str = None):
    """
    Get existing profile or create a new one.
    Returns the profile UUID.
    """
    # Check if profile exists
    res = supabase.table("profiles").select("id").eq("full_name", full_name).execute()
    
    if res.data:
        return res.data[0]['id']
    
    # Create new profile
    contact_info = {"email": email} if email else {}
    new_profile = supabase.table("profiles").insert({
        "full_name": full_name,
        "contact_info": contact_info,
        "summary": summary or f"Job seeker profile for {full_name}"
    }).execute()
    
    return new_profile.data[0]['id']


def create_mission(full_name: str, job_role: str, jobs_per_day: int, duration_days: int, email: str = None):
    """
    Initialize a new mission/campaign for a user.
    This function is called by your UI (Streamlit/React) when user submits the form.
    
    Campaign config is stored in the history JSONB field as a special entry.
    """
    
    # Get or create user profile
    user_id = get_or_create_profile(full_name, email, f"Looking for {job_role} positions")
    
    # Campaign config stored in history as first entry
    campaign_config = {
        "type": "campaign_config",
        "target_role": job_role,
        "daily_limit": jobs_per_day,
        "total_days": duration_days,
        "start_date": str(date.today()),
        "current_day": 1,
        "jobs_applied_today": 0,
        "is_active": True
    }

    # Initialize the agent in Supabase
    result = supabase.table("agent_states").upsert({
        "user_id": user_id,
        "thought_signature": None,
        "internal_summary": f"Mission Started: {job_role} for {duration_days} days.",
        "thinking_level": "low",
        "history": [campaign_config]  # Store config as first history entry
    }, on_conflict="user_id").execute()
    
    print(f"✅ Mission initialized for {full_name} ({user_id[:8]}...): {job_role}, {jobs_per_day}/day for {duration_days} days")
    return result


def scout_jobs(query: str, location: str = "Remote"):
    """
    Placeholder function to scout for jobs.
    In production, this would call job APIs (LinkedIn, Indeed, etc.)
    """
    # Simulate finding jobs
    return [
        {"title": f"{query} Developer", "company": "Tech Corp", "location": location, "url": "https://example.com/job1"},
        {"title": f"Senior {query}", "company": "StartupXYZ", "location": location, "url": "https://example.com/job2"},
        {"title": f"Junior {query}", "company": "BigCo", "location": location, "url": "https://example.com/job3"},
    ]


def get_campaign_config(history: list) -> dict:
    """
    Extract campaign config from history.
    The config is stored as the first entry with type='campaign_config'.
    """
    for entry in history:
        if isinstance(entry, dict) and entry.get('type') == 'campaign_config':
            return entry
    return None


def run_all_user_campaigns():
    """Process all active user campaigns."""
    
    # 1. Fetch ALL agent states with their profiles
    response = supabase.table("agent_states").select("*, profiles(full_name)").execute()
    
    # Filter for active campaigns (check history for campaign_config with is_active=True)
    active_agents = []
    for agent in response.data:
        config = get_campaign_config(agent.get('history', []))
        if config and config.get('is_active', False):
            active_agents.append(agent)
    
    print(f"🚀 Found {len(active_agents)} active missions to process.")

    for agent_state in active_agents:
        try:
            process_single_agent(agent_state)
        except Exception as e:
            print(f"❌ Error processing user {agent_state.get('user_id')}: {e}")


def process_single_agent(state: dict):
    """Process a single user's campaign according to their configuration."""
    
    user_id = state.get('user_id')
    history = state.get('history', [])
    config = get_campaign_config(history)
    
    if not config:
        print(f"⚠️ User {user_id[:8]}...: No campaign config found.")
        return
    
    profile_name = state.get('profiles', {}).get('full_name', 'Unknown')
    
    # --- RULE CHECKING ENGINE ---
    
    # Rule 1: Is the marathon over?
    if config.get('current_day', 1) > config.get('total_days', 1):
        print(f"🏁 {profile_name}: Mission Complete.")
        config['is_active'] = False
        update_agent_state(user_id, history, "Mission Finished!")
        return

    # Rule 2: Did we already finish today's quota?
    if config.get('jobs_applied_today', 0) >= config.get('daily_limit', 3):
        print(f"💤 {profile_name}: Daily quota met.")
        return

    # --- EXECUTION ENGINE ---
    
    target_role = config.get('target_role', 'Software Developer')
    daily_limit = config.get('daily_limit', 3)
    current_day = config.get('current_day', 1)
    
    print(f"▶️ {profile_name}: Day {current_day} - Finding {daily_limit} jobs for '{target_role}'...")
    
    # 1. Scout (Using the USER'S target role)
    jobs = scout_jobs(query=target_role, location="Remote")
    
    # 2. Process jobs (Loop until we hit THE USER'S daily limit)
    jobs_processed = 0
    for job in jobs:
        if jobs_processed >= daily_limit:
            break
        
        # Generate cover letter using Gemini
        prompt = f"Write a brief, professional cover letter for the position: {job['title']} at {job['company']}"
        
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(include_thoughts=True)
                )
            )
            
            cover_letter = response.text
            print(f"  ✓ Generated cover letter for {job['title']} at {job['company']}")
            
            # Save application to job_applications table
            supabase.table("job_applications").insert({
                "user_id": user_id,
                "job_title": job['title'],
                "company_name": job['company'],
                "source_url": job.get('url'),
                "status": "scouted",
                "replies_log": [{"action": "cover_letter_generated", "content": cover_letter[:500], "timestamp": datetime.utcnow().isoformat()}]
            }).execute()
            
        except Exception as e:
            print(f"  ✗ Error generating cover letter: {e}")
        
        jobs_processed += 1

    # --- STATE UPDATE ENGINE ---
    
    config['jobs_applied_today'] = jobs_processed
    config['current_day'] = current_day + 1
    
    # Reset daily counter for next day
    config['jobs_applied_today'] = 0
    
    # Add a history entry for this run
    history.append({
        "type": "daily_run",
        "day": current_day,
        "jobs_processed": jobs_processed,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    update_agent_state(user_id, history, f"Day {current_day}: Applied to {jobs_processed} jobs.")
    print(f"✅ {profile_name}: Day {current_day} complete. Applied to {jobs_processed} jobs.")


def update_agent_state(user_id: str, history: list, summary: str):
    """Update the user's agent state in Supabase."""
    
    supabase.table("agent_states").update({
        "history": history,
        "internal_summary": summary,
        "last_updated": datetime.utcnow().isoformat()
    }).eq("user_id", user_id).execute()


# --- Demo Functions ---

def demo_create_missions():
    """Create sample missions for testing."""
    
    # User A: Conservative approach
    create_mission(
        full_name="Alice Developer",
        job_role="Python Developer",
        jobs_per_day=3,
        duration_days=3,
        email="alice@example.com"
    )
    
    # User B: Aggressive approach
    create_mission(
        full_name="Bob Analyst",
        job_role="SQL Analyst",
        jobs_per_day=10,
        duration_days=4,
        email="bob@example.com"
    )


def show_applications(full_name: str = None):
    """Show job applications for a user or all users."""
    
    if full_name:
        # Get user_id from profile
        profile = supabase.table("profiles").select("id").eq("full_name", full_name).execute()
        if not profile.data:
            print(f"No profile found for {full_name}")
            return
        
        user_id = profile.data[0]['id']
        apps = supabase.table("job_applications").select("*").eq("user_id", user_id).execute()
    else:
        apps = supabase.table("job_applications").select("*, profiles(full_name)").execute()
    
    print(f"\n📋 Job Applications ({len(apps.data)} total):")
    for app in apps.data:
        print(f"  - {app['job_title']} at {app['company_name']} [{app['status']}]")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            print("🎯 Creating demo missions...")
            demo_create_missions()
        elif sys.argv[1] == "--show":
            show_applications()
    else:
        print("🏃 Running all user campaigns...")
        run_all_user_campaigns()
