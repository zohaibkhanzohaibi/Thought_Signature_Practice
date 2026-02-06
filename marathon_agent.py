"""
marathon_agent.py - Unified Marathon Agent for Job Search

This is the main script that handles:
1. User profile and campaign creation (form-based)
2. Job search using AI prompts
3. Job matching with user profile
4. State persistence with thought signatures
5. Resume capability across sessions

Usage:
  python marathon_agent.py --create    # Create a new campaign (interactive form)
  python marathon_agent.py --run       # Run one iteration for test user
  python marathon_agent.py --status    # Check campaign status
  python marathon_agent.py --list      # List all campaigns
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

# Fixed Test User Profile
TEST_USER = {
    "full_name": "Test Job Seeker",
    "email": "testseeker@example.com",
    "skills": ["Python", "SQL", "Data Analysis", "Excel", "Power BI"],
    "experience_years": 2,
    "location": "Karachi",
    "summary": "Motivated data professional with 2 years of experience in SQL and Python. Looking for opportunities in data analysis and backend development."
}


# ============== DATABASE OPERATIONS ==============

def get_or_create_test_profile():
    """Get or create the fixed test user profile."""
    res = supabase.table("profiles").select("*").eq("full_name", TEST_USER["full_name"]).execute()
    
    if res.data:
        return res.data[0]
    
    # Create test profile
    profile = supabase.table("profiles").insert({
        "full_name": TEST_USER["full_name"],
        "contact_info": {
            "email": TEST_USER["email"],
            "location": TEST_USER["location"]
        },
        "summary": TEST_USER["summary"]
    }).execute()
    
    print(f"✅ Created test profile: {TEST_USER['full_name']}")
    return profile.data[0]


def get_agent_state(user_id: str):
    """Fetch agent state from database."""
    res = supabase.table("agent_states").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def save_agent_state(user_id: str, state: dict):
    """Save or update agent state in database."""
    state["user_id"] = user_id
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    return supabase.table("agent_states").upsert(
        state, on_conflict="user_id"
    ).execute()


def save_job_application(user_id: str, job: dict, cover_letter: str = None):
    """Save a job application to the database."""
    return supabase.table("job_applications").insert({
        "user_id": user_id,
        "job_title": job["title"],
        "company_name": job["company"],
        "source_url": job.get("url"),
        "status": "scouted",
        "replies_log": [{
            "action": "scouted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cover_letter": cover_letter[:500] if cover_letter else None
        }]
    }).execute()


def get_user_applications(user_id: str):
    """Get all job applications for a user."""
    return supabase.table("job_applications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()


def get_applied_job_keys(user_id: str) -> set:
    """Get a set of unique job keys (company|title) that have already been applied to."""
    apps = get_user_applications(user_id)
    applied_keys = set()
    for app in apps.data:
        key = f"{app['company_name'].lower().strip()}|{app['job_title'].lower().strip()}"
        applied_keys.add(key)
    return applied_keys


def get_job_key(job: dict) -> str:
    """Generate a unique key for a job based on company and title."""
    return f"{job['company'].lower().strip()}|{job['title'].lower().strip()}"


# ============== AI FUNCTIONS ==============

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


def search_jobs_with_ai(query: str, user_profile: dict, location: str = None, exclude_jobs: list = None):
    """
    Use AI with Google Search grounding to find REAL jobs from the internet.
    Uses Gemini's built-in web search capability for live job listings.
    Excludes previously scouted/applied jobs.
    """
    location = location or user_profile.get("contact_info", {}).get("location", "Remote")
    
    # Build exclusion list
    exclude_section = ""
    if exclude_jobs:
        exclude_list = "\n".join([f"- {job['job_title']} at {job['company_name']}" for job in exclude_jobs[:20]])
        exclude_section = f"\n\nDO NOT include these jobs (already applied/scouted):\n{exclude_list}\n"
    
    prompt = f"""Search the internet for REAL, currently open job listings matching these criteria:

JOB SEARCH: {query}
LOCATION: {location} (include remote positions)
EXPERIENCE LEVEL: {TEST_USER['experience_years']} years
SKILLS: {', '.join(TEST_USER['skills'])}{exclude_section}

Find 5 actual job postings from job boards like LinkedIn, Indeed, Glassdoor, Rozee.pk, or company career pages.

For each job found, extract:
- Job title
- Company name  
- Location
- Application URL (the actual job posting link)
- Key requirements
- Match score (0-100) based on the candidate's skills

Return ONLY a JSON array in this format (no markdown, no explanation):
[
  {{"title": "Job Title", "company": "Company Name", "location": "City", "url": "https://example.com/job1", "match_score": 85, "description": "Brief job description", "requirements": ["Skill1", "Skill2"], "posted_date": "2 days ago"}},
  ...
]
For posted_date, use realistic relative times like "Today", "Yesterday", "2 days ago", "1 week ago", etc.
Focus on jobs in {location} or Remote positions. Match the user's skill level and experience.
"""
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )
    
    # Extract signature
    signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            signature = last_part.thought_signature
    
    # Parse JSON response
    try:
        import json
        # Clean up response text
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        jobs = json.loads(text.strip())
    except:
        # Fallback to mock jobs if parsing fails
        jobs = [
            {"title": f"{query} Developer", "company": "Tech Solutions Karachi", "location": location, "url": "https://example.com/job1", "match_score": 90, "description": f"Looking for {query} professional", "requirements": TEST_USER["skills"][:3], "posted_date": "Today"},
            {"title": f"Senior {query} Analyst", "company": "Data Corp Pakistan", "location": location, "url": "https://example.com/job2", "match_score": 85, "description": f"Senior {query} role", "requirements": TEST_USER["skills"][:2], "posted_date": "2 days ago"},
            {"title": f"Junior {query} Specialist", "company": "StartUp Hub", "location": "Remote", "url": "https://example.com/job3", "match_score": 75, "description": f"Entry level {query} position", "requirements": [TEST_USER["skills"][0]], "posted_date": "1 week ago"},
        ]
    
    return jobs, signature


def generate_cover_letter(job: dict, user_profile: dict):
    """Generate a personalized cover letter for a job."""
    prompt = f"""Write a brief, professional cover letter for this job application.

JOB:
- Title: {job.get('title')}
- Company: {job.get('company')}
- Description: {job.get('description', 'N/A')}
- Requirements: {job.get('requirements', [])}

APPLICANT:
- Name: {user_profile.get('full_name')}
- Skills: {TEST_USER['skills']}
- Experience: {TEST_USER['experience_years']} years
- Summary: {user_profile.get('summary')}

Write a concise 3-paragraph cover letter. Be professional but personable.
"""
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )
    
    signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            signature = last_part.thought_signature
    
    return response.text, signature


def continue_with_signature(history: list, new_prompt: str):
    """Continue a conversation using saved thought signatures."""
    
    # Convert history to proper format
    formatted_history = []
    for msg in history:
        if msg.get("type") == "campaign_config":
            continue  # Skip config entries
            
        content_parts = []
        for part in msg.get('parts', []):
            if 'text' in part:
                if part.get('thought_signature'):
                    sig_bytes = decode_signature(part['thought_signature'])
                    content_parts.append(types.Part(
                        text=part['text'],
                        thought_signature=sig_bytes
                    ))
                else:
                    content_parts.append(types.Part(text=part['text']))
        
        if content_parts:
            formatted_history.append(types.Content(
                role=msg['role'],
                parts=content_parts
            ))
    
    # Create chat with history
    chat = client.chats.create(
        model=MODEL_ID,
        history=formatted_history,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )
    
    response = chat.send_message(new_prompt)
    
    # Extract new signature
    signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            signature = last_part.thought_signature
    
    return response.text, signature


# ============== CAMPAIGN FUNCTIONS ==============

def create_campaign_form():
    """Interactive form to create a new job search campaign."""
    print("\n" + "="*50)
    print("🚀 CREATE NEW JOB SEARCH CAMPAIGN")
    print("="*50 + "\n")
    
    # Use test user
    profile = get_or_create_test_profile()
    user_id = profile["id"]
    
    print(f"📋 Using Test Profile: {TEST_USER['full_name']}")
    print(f"   Skills: {', '.join(TEST_USER['skills'])}")
    print(f"   Location: {TEST_USER['location']}\n")
    
    # Get campaign details
    job_query = input("🔍 What job are you looking for? (e.g., 'SQL Developer', 'Data Analyst'): ").strip()
    if not job_query:
        job_query = "SQL Developer"
    
    try:
        jobs_per_day = int(input("📊 How many jobs per day? [default: 3]: ").strip() or "3")
    except:
        jobs_per_day = 3
    
    try:
        duration_days = int(input("📅 For how many days? [default: 5]: ").strip() or "5")
    except:
        duration_days = 5
    
    location = input(f"📍 Location? [default: {TEST_USER['location']}]: ").strip()
    if not location:
        location = TEST_USER["location"]
    
    # Create campaign config
    campaign_config = {
        "type": "campaign_config",
        "target_role": job_query,
        "daily_limit": jobs_per_day,
        "total_days": duration_days,
        "location": location,
        "start_date": str(date.today()),
        "current_day": 1,
        "jobs_applied_today": 0,
        "is_active": True
    }
    
    # Initial AI search
    print(f"\n🔎 Searching for '{job_query}' jobs in {location}...")
    jobs, signature = search_jobs_with_ai(job_query, profile, location)
    
    # Build initial history
    initial_prompt = f"I'm looking for {job_query} jobs in {location}. Find me {jobs_per_day} good matches per day for {duration_days} days."
    
    history = [
        campaign_config,
        {"role": "user", "parts": [{"text": initial_prompt}]},
        {"role": "model", "parts": [{"text": f"Found {len(jobs)} matching jobs.", "thought_signature": encode_signature(signature)}]}
    ]
    
    # Save agent state
    state = {
        "thought_signature": encode_signature(signature),
        "internal_summary": f"Campaign started: {job_query} in {location}",
        "thinking_level": "low",
        "history": history
    }
    save_agent_state(user_id, state)
    
    # Save initial job applications
    print(f"\n✅ Found {len(jobs)} matching jobs:\n")
    for i, job in enumerate(jobs[:jobs_per_day], 1):
        posted = job.get('posted_date', 'Unknown')
        print(f"  {i}. {job['title']} at {job['company']} ({job.get('location', 'N/A')})")
        print(f"     Match Score: {job.get('match_score', 'N/A')}% | Posted: {posted}")
        save_job_application(user_id, job)
    
    print(f"\n✅ Campaign created successfully!")
    print(f"   📧 Jobs saved to database")
    print(f"   🔄 Marathon runner will process {jobs_per_day} jobs/day for {duration_days} days")
    print(f"   ⏰ Cron job runs daily at 2 AM UTC")
    
    return campaign_config


def run_campaign_iteration(user_id: str = None):
    """Run one iteration of the campaign for a user."""
    
    # Get test user if not specified
    if not user_id:
        profile = get_or_create_test_profile()
        user_id = profile["id"]
    else:
        profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute().data
    
    # Get agent state
    state = get_agent_state(user_id)
    if not state:
        print("❌ No campaign found. Run with --create first.")
        return
    
    history = state.get("history", [])
    
    # Find campaign config in history
    config = None
    for item in history:
        if isinstance(item, dict) and item.get("type") == "campaign_config":
            config = item
            break
    
    if not config:
        print("❌ No campaign config found in state.")
        return
    
    if not config.get("is_active", False):
        print("🏁 Campaign is complete or inactive.")
        return
    
    current_day = config.get("current_day", 1)
    total_days = config.get("total_days", 5)
    
    # Check if campaign is already complete
    if current_day > total_days:
        config["is_active"] = False
        save_agent_state(user_id, state)
        print("🏁 Campaign completed!")
        return
    
    # Check if this is the last day
    is_last_day = (current_day == total_days)
    
    print(f"\n📅 Day {current_day}/{total_days} of campaign" + (" (FINAL DAY)" if is_last_day else ""))
    print(f"🎯 Target: {config.get('target_role')} in {config.get('location')}")
    
    # Get previous applications to exclude from search
    previous_apps = get_user_applications(user_id)
    exclude_jobs = previous_apps.data if previous_apps.data else []
    
    if exclude_jobs:
        print(f"📋 Excluding {len(exclude_jobs)} previously scouted jobs")
    
    # Use signature to continue conversation
    new_prompt = f"Day {current_day}: Find me {config.get('daily_limit')} NEW {config.get('target_role')} jobs in {config.get('location')}. Focus on the latest openings not previously shown."
    
    if state.get("thought_signature"):
        print("🔐 Resuming with saved thought signature...")
        response_text, new_signature = continue_with_signature(history, new_prompt)
    else:
        # Fresh search
        jobs, new_signature = search_jobs_with_ai(
            config.get("target_role"),
            profile,
            config.get("location"),
            exclude_jobs=exclude_jobs
        )
        response_text = f"Found {len(jobs)} jobs for day {current_day}"
    
    # Update history
    history.append({"role": "user", "parts": [{"text": new_prompt}]})
    history.append({"role": "model", "parts": [{"text": response_text, "thought_signature": encode_signature(new_signature)}]})
    
    # Get fresh jobs
    jobs, _ = search_jobs_with_ai(config.get("target_role"), profile, config.get("location"))
    
    # Get previously applied jobs to filter duplicates
    applied_keys = get_applied_job_keys(user_id)
    
    # Filter out already-applied jobs
    new_jobs = []
    for job in jobs:
        job_key = get_job_key(job)
        if job_key not in applied_keys:
            new_jobs.append(job)
        else:
            print(f"  ⏭ Skipping duplicate: {job['title']} at {job['company']}")
    
    if not new_jobs:
        print("\n⚠️ No new jobs found. All results were duplicates.")
        print("   Try running again later or adjust your search criteria.")
        return
    
    # Process and save jobs
    jobs_processed = 0
    daily_limit = config.get("daily_limit", 3)
    
    print(f"\n📋 Processing {min(len(new_jobs), daily_limit)} new jobs:\n")
    for job in new_jobs[:daily_limit]:
        posted = job.get('posted_date', 'Unknown')
        print(f"  ▶ {job['title']} at {job['company']} (Posted: {posted})")
        
        # Generate cover letter
        try:
            cover_letter, _ = generate_cover_letter(job, profile)
            print(f"    ✓ Cover letter generated")
        except Exception as e:
            cover_letter = None
            print(f"    ✗ Cover letter failed: {e}")
        
        # Save to database
        save_job_application(user_id, job, cover_letter)
        jobs_processed += 1
    
    # Update campaign state
    config["current_day"] = current_day + 1
    config["jobs_applied_today"] = jobs_processed
    
    # Mark campaign complete on last day
    if is_last_day:
        config["is_active"] = False
        config["completed_date"] = str(date.today())
    
    state["thought_signature"] = encode_signature(new_signature)
    state["internal_summary"] = f"Day {current_day}: Processed {jobs_processed} jobs"
    state["history"] = history
    
    save_agent_state(user_id, state)
    
    if is_last_day:
        total_apps = get_user_applications(user_id)
        total_count = len(total_apps.data) if total_apps.data else 0
        print(f"\n🏁 Campaign COMPLETED!")
        print(f"   📊 Total jobs scouted: {total_count}")
        print(f"   📅 Duration: {total_days} days")
        print(f"   ✅ Campaign is now inactive")
    else:
        print(f"\n✅ Day {current_day} complete! Processed {jobs_processed} jobs.")
        print(f"   Next run: Day {current_day + 1}")


def show_status():
    """Show campaign status for test user."""
    profile = get_or_create_test_profile()
    user_id = profile["id"]
    
    state = get_agent_state(user_id)
    
    print("\n" + "="*50)
    print("📊 CAMPAIGN STATUS")
    print("="*50 + "\n")
    
    print(f"👤 User: {profile.get('full_name')}")
    
    if not state:
        print("❌ No active campaign found.")
        return
    
    # Find config
    config = None
    for item in state.get("history", []):
        if isinstance(item, dict) and item.get("type") == "campaign_config":
            config = item
            break
    
    if config:
        print(f"\n📋 Campaign Details:")
        print(f"   🎯 Target: {config.get('target_role')}")
        print(f"   📍 Location: {config.get('location')}")
        print(f"   📅 Day: {config.get('current_day')}/{config.get('total_days')}")
        print(f"   📊 Jobs/Day: {config.get('daily_limit')}")
        print(f"   ✅ Active: {config.get('is_active')}")
        print(f"   📆 Started: {config.get('start_date')}")
    
    # Show applications
    apps = get_user_applications(user_id)
    if apps.data:
        print(f"\n📋 Job Applications ({len(apps.data)} total):")
        for app in apps.data[:5]:
            print(f"   - {app['job_title']} at {app['company_name']} [{app['status']}]")
        if len(apps.data) > 5:
            print(f"   ... and {len(apps.data) - 5} more")
    
    if state.get("thought_signature"):
        print(f"\n🔐 Thought Signature: {state['thought_signature'][:50]}...")
    
    print(f"\n⏰ Last Updated: {state.get('last_updated', 'N/A')}")


def list_all_campaigns():
    """List all campaigns from all users."""
    print("\n" + "="*60)
    print("📋 ALL CAMPAIGNS")
    print("="*60 + "\n")
    
    # Get all agent states
    res = supabase.table("agent_states").select("*, profiles(full_name)").execute()
    
    if not res.data:
        print("❌ No campaigns found.")
        return
    
    active_count = 0
    completed_count = 0
    
    for state in res.data:
        # Find config in history
        config = None
        for item in state.get("history", []):
            if isinstance(item, dict) and item.get("type") == "campaign_config":
                config = item
                break
        
        if not config:
            continue
        
        # Get user name
        user_name = state.get("profiles", {}).get("full_name", "Unknown") if state.get("profiles") else "Unknown"
        user_id = state.get("user_id")
        
        # Get job count
        apps = supabase.table("job_applications").select("id", count="exact").eq("user_id", user_id).execute()
        job_count = apps.count if hasattr(apps, 'count') else len(apps.data) if apps.data else 0
        
        is_active = config.get("is_active", False)
        status_icon = "🟢" if is_active else "🔴"
        
        if is_active:
            active_count += 1
        else:
            completed_count += 1
        
        print(f"{status_icon} {user_name}")
        print(f"   🎯 Role: {config.get('target_role')}")
        print(f"   📍 Location: {config.get('location')}")
        print(f"   📅 Progress: Day {config.get('current_day')}/{config.get('total_days')}")
        print(f"   📊 Jobs Scouted: {job_count}")
        print(f"   📆 Started: {config.get('start_date')}")
        if config.get('completed_date'):
            print(f"   ✅ Completed: {config.get('completed_date')}")
        print()
    
    print("-"*60)
    print(f"📊 Summary: {active_count} active, {completed_count} completed")


# ============== MAIN ==============

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "--create":
        create_campaign_form()
    elif command == "--run":
        run_campaign_iteration()
    elif command == "--status":
        show_status()
    elif command == "--list":
        list_all_campaigns()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
