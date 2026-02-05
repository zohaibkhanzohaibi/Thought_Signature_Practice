"""
universal_marathon_runner.py - Cron Job Runner for GitHub Actions

This script is executed by GitHub Actions every 6 hours.
It processes ALL active user campaigns and saves results to the database.

Usage:
  python universal_marathon_runner.py           # Run all active campaigns
  python universal_marathon_runner.py --demo    # Create demo campaigns
"""

import os
import sys
import base64
from datetime import date, datetime, timezone
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Setup Clients
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

MODEL_ID = "gemini-3-flash-preview"


# ============== UTILITY FUNCTIONS ==============

def encode_signature(sig):
    """Encode signature bytes to base64 string."""
    if sig and isinstance(sig, bytes):
        return base64.b64encode(sig).decode('utf-8')
    return sig


def decode_signature(sig_b64):
    """Decode base64 string to signature bytes."""
    if sig_b64 and isinstance(sig_b64, str):
        return base64.b64decode(sig_b64)
    return sig_b64


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")


# ============== DATABASE OPERATIONS ==============

def get_all_active_campaigns():
    """Fetch all agent states with active campaigns."""
    response = supabase.table("agent_states").select("*, profiles(*)").execute()
    
    active = []
    for agent in response.data:
        history = agent.get("history", [])
        for item in history:
            if isinstance(item, dict) and item.get("type") == "campaign_config":
                if item.get("is_active", False):
                    agent["_config"] = item
                    active.append(agent)
                break
    
    return active


def save_agent_state(user_id: str, state: dict):
    """Update agent state in database."""
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    return supabase.table("agent_states").update(state).eq("user_id", user_id).execute()


def save_job_application(user_id: str, job: dict, cover_letter: str = None):
    """Save a job application to the database."""
    return supabase.table("job_applications").insert({
        "user_id": user_id,
        "job_title": job["title"],
        "company_name": job["company"],
        "source_url": job.get("url"),
        "status": "scouted",
        "replies_log": [{
            "action": "scouted_by_cron",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cover_letter_preview": cover_letter[:300] if cover_letter else None
        }]
    }).execute()


# ============== AI FUNCTIONS ==============

def search_jobs_with_ai(query: str, profile: dict, location: str):
    """Use AI to generate job search results based on user profile."""
    
    summary = profile.get("summary", "")
    contact_info = profile.get("contact_info", {})
    
    prompt = f"""You are a job search assistant. Generate 5 realistic job listings matching this search.

USER: {profile.get('full_name')}
SUMMARY: {summary}
LOCATION PREFERENCE: {location}

JOB QUERY: {query}

Return ONLY valid JSON array (no markdown):
[
  {{"title": "Job Title", "company": "Company", "location": "City", "url": "https://example.com/job", "match_score": 85, "description": "Brief description"}}
]
"""
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True)
            )
        )
        
        # Extract signature
        signature = None
        if response.candidates and response.candidates[0].content.parts:
            last_part = response.candidates[0].content.parts[-1]
            if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
                signature = last_part.thought_signature
        
        # Parse response
        import json
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        jobs = json.loads(text.strip())
        return jobs, signature
        
    except Exception as e:
        log(f"  ⚠️ AI search failed: {e}")
        # Return fallback jobs
        return [
            {"title": f"{query} Developer", "company": "Tech Company", "location": location, "url": "https://example.com/1", "match_score": 80, "description": f"{query} position"},
            {"title": f"Senior {query}", "company": "Startup Inc", "location": location, "url": "https://example.com/2", "match_score": 75, "description": f"Senior {query} role"},
        ], None


def generate_cover_letter(job: dict, profile: dict):
    """Generate a brief cover letter for a job."""
    try:
        prompt = f"""Write a brief 2-paragraph cover letter.

JOB: {job.get('title')} at {job.get('company')}
APPLICANT: {profile.get('full_name')}
PROFILE: {profile.get('summary', 'Experienced professional')}

Be professional and concise."""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        return response.text
    except Exception as e:
        log(f"  ⚠️ Cover letter failed: {e}")
        return None


# ============== MAIN PROCESSING ==============

def process_single_campaign(agent_state: dict):
    """Process one user's campaign."""
    
    user_id = agent_state.get("user_id")
    profile = agent_state.get("profiles", {})
    config = agent_state.get("_config", {})
    history = agent_state.get("history", [])
    
    full_name = profile.get("full_name", user_id[:8])
    current_day = config.get("current_day", 1)
    total_days = config.get("total_days", 5)
    daily_limit = config.get("daily_limit", 3)
    target_role = config.get("target_role", "Software Developer")
    location = config.get("location", "Remote")
    
    log(f"▶️ {full_name}: Day {current_day}/{total_days} - {target_role}")
    
    # Check if campaign is complete
    if current_day > total_days:
        log(f"  🏁 Campaign complete!")
        config["is_active"] = False
        save_agent_state(user_id, {"history": history})
        return
    
    # Search for jobs
    jobs, signature = search_jobs_with_ai(target_role, profile, location)
    log(f"  📋 Found {len(jobs)} jobs")
    
    # Process jobs up to daily limit
    jobs_processed = 0
    for job in jobs[:daily_limit]:
        log(f"  ✓ {job['title']} at {job['company']}")
        
        # Generate cover letter
        cover_letter = generate_cover_letter(job, profile)
        
        # Save to database
        try:
            save_job_application(user_id, job, cover_letter)
            jobs_processed += 1
        except Exception as e:
            log(f"  ⚠️ Failed to save: {e}")
    
    # Update campaign state
    config["current_day"] = current_day + 1
    config["jobs_applied_today"] = jobs_processed
    
    # Update history
    history.append({
        "role": "system",
        "parts": [{"text": f"Day {current_day}: Processed {jobs_processed} jobs via cron"}],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Save state
    save_agent_state(user_id, {
        "thought_signature": encode_signature(signature) if signature else agent_state.get("thought_signature"),
        "history": history,
        "internal_summary": f"Cron Day {current_day}: {jobs_processed} jobs processed"
    })
    
    log(f"  ✅ Day {current_day} complete: {jobs_processed} jobs saved")


def run_all_campaigns():
    """Main function to process all active campaigns."""
    
    log("=" * 50)
    log("🚀 MARATHON AGENT - CRON JOB RUNNER")
    log("=" * 50)
    
    active_campaigns = get_all_active_campaigns()
    log(f"📊 Found {len(active_campaigns)} active campaigns")
    
    if not active_campaigns:
        log("💤 No active campaigns to process")
        return
    
    for agent_state in active_campaigns:
        try:
            process_single_campaign(agent_state)
        except Exception as e:
            user_id = agent_state.get("user_id", "unknown")
            log(f"❌ Error processing {user_id[:8]}...: {e}")
    
    log("=" * 50)
    log("✅ CRON JOB COMPLETE")
    log("=" * 50)


def create_demo_campaigns():
    """Create demo campaigns for testing."""
    
    log("🎯 Creating demo campaigns...")
    
    # Demo user 1
    profile1 = supabase.table("profiles").upsert({
        "full_name": "Demo User Python",
        "contact_info": {"email": "demo1@example.com", "location": "Karachi"},
        "summary": "Python developer with 3 years experience in Django and FastAPI"
    }, on_conflict="full_name").execute()
    
    user_id = profile1.data[0]["id"]
    
    config = {
        "type": "campaign_config",
        "target_role": "Python Developer",
        "daily_limit": 3,
        "total_days": 3,
        "location": "Karachi",
        "start_date": str(date.today()),
        "current_day": 1,
        "jobs_applied_today": 0,
        "is_active": True
    }
    
    supabase.table("agent_states").upsert({
        "user_id": user_id,
        "thought_signature": None,
        "internal_summary": "Demo campaign created",
        "thinking_level": "low",
        "history": [config]
    }, on_conflict="user_id").execute()
    
    log(f"✅ Created demo campaign for: Demo User Python")
    log(f"   Target: Python Developer, 3 jobs/day for 3 days")


# ============== MAIN ==============

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        create_demo_campaigns()
    else:
        run_all_campaigns()
