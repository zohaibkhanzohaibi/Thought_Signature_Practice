"""
universal_marathon_runner.py - Multi-User Campaign Processor

This script runs as a background job (via GitHub Actions or Cron) and processes
ALL active user campaigns according to their individual configurations.
"""

import os
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


def create_mission(user_id: str, job_role: str, jobs_per_day: int, duration_days: int):
    """
    Initialize a new mission/campaign for a user.
    This function is called by your UI (Streamlit/React) when user submits the form.
    """
    
    config = {
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
        "campaign_config": config,
        "internal_summary": f"Mission Started: {job_role} for {duration_days} days.",
        "thinking_level": "low",
        "history": [],
        "last_signature": None
    }).execute()
    
    print(f"✅ Mission initialized for {user_id}: {job_role}, {jobs_per_day}/day for {duration_days} days")
    return result


def scout_jobs(query: str, location: str = "Remote"):
    """
    Placeholder function to scout for jobs.
    In production, this would call job APIs (LinkedIn, Indeed, etc.)
    """
    # Simulate finding jobs
    return [
        {"title": f"{query} Developer", "company": "Tech Corp", "location": location},
        {"title": f"Senior {query}", "company": "StartupXYZ", "location": location},
        {"title": f"Junior {query}", "company": "BigCo", "location": location},
    ]


def run_all_user_campaigns():
    """Process all active user campaigns."""
    
    # 1. Fetch ALL users who have an active campaign
    # We use a JSON filter to only get active missions
    response = supabase.table("agent_states").select("*").execute()
    
    # Filter for active campaigns
    active_agents = [
        agent for agent in response.data 
        if agent.get('campaign_config', {}).get('is_active', False)
    ]
    
    print(f"🚀 Found {len(active_agents)} active missions to process.")

    for agent_state in active_agents:
        try:
            process_single_agent(agent_state)
        except Exception as e:
            print(f"❌ Error processing user {agent_state.get('user_id')}: {e}")


def process_single_agent(state: dict):
    """Process a single user's campaign according to their configuration."""
    
    config = state.get('campaign_config', {})
    user_id = state.get('user_id')
    
    if not config:
        print(f"⚠️ User {user_id}: No campaign config found.")
        return
    
    # --- RULE CHECKING ENGINE ---
    
    # Rule 1: Is the marathon over?
    if config.get('current_day', 1) > config.get('total_days', 1):
        print(f"🏁 User {user_id}: Mission Complete.")
        config['is_active'] = False
        update_db(user_id, config, "Mission Finished!")
        return

    # Rule 2: Did we already finish today's quota?
    if config.get('jobs_applied_today', 0) >= config.get('daily_limit', 3):
        print(f"💤 User {user_id}: Daily quota met.")
        return

    # --- EXECUTION ENGINE ---
    
    target_role = config.get('target_role', 'Software Developer')
    daily_limit = config.get('daily_limit', 3)
    
    print(f"▶️ User {user_id}: Finding {daily_limit} jobs for '{target_role}'...")
    
    # 1. Scout (Using the USER'S target role)
    jobs = scout_jobs(query=target_role, location="Remote")
    
    # 2. Process jobs (Loop until we hit THE USER'S daily limit)
    jobs_processed = 0
    for job in jobs:
        if jobs_processed >= daily_limit:
            break
        
        # Generate cover letter using Gemini
        prompt = f"Write a brief cover letter for the position: {job['title']} at {job['company']}"
        
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
            
            # Save application to database (you could create a separate table for this)
            # supabase.table("job_applications").insert({...}).execute()
            
        except Exception as e:
            print(f"  ✗ Error generating cover letter: {e}")
        
        jobs_processed += 1

    # --- STATE UPDATE ENGINE ---
    
    config['jobs_applied_today'] = jobs_processed
    current_day = config.get('current_day', 1)
    config['current_day'] = current_day + 1
    
    # Reset daily counter for next day
    config['jobs_applied_today'] = 0
    
    update_db(user_id, config, f"Day {current_day}: Applied to {jobs_processed} jobs.")
    print(f"✅ User {user_id}: Day {current_day} complete. Applied to {jobs_processed} jobs.")


def update_db(user_id: str, config: dict, summary: str):
    """Update the user's campaign state in Supabase."""
    
    supabase.table("agent_states").update({
        "campaign_config": config,
        "internal_summary": summary,
        "last_updated": datetime.utcnow().isoformat()
    }).eq("user_id", user_id).execute()


# --- Demo Functions ---

def demo_create_missions():
    """Create sample missions for testing."""
    
    # User A: Conservative approach
    create_mission(
        user_id="user_a_conservative",
        job_role="Python Developer",
        jobs_per_day=3,
        duration_days=3
    )
    
    # User B: Aggressive approach
    create_mission(
        user_id="user_b_aggressive",
        job_role="SQL Analyst",
        jobs_per_day=10,
        duration_days=4
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("🎯 Creating demo missions...")
        demo_create_missions()
    else:
        print("🏃 Running all user campaigns...")
        run_all_user_campaigns()
