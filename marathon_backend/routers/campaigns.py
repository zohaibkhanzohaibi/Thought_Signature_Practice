"""
Campaigns Router - Job search campaign management endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

from ..models.database import MarathonDB
from ..models.schemas import CampaignCreate, CampaignResponse, CampaignRunResponse
from ..services.job_search import JobSearchAgent

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])
db = MarathonDB()


def _calculate_campaign_status(config: dict) -> dict:
    """Calculate campaign status, current day, and days remaining."""
    started_at = config.get("started_at") or config.get("created_at")
    total_days = config.get("total_days", 7)
    is_paused = config.get("paused", False)
    is_completed = config.get("completed", False)
    
    if not started_at:
        return {
            "status": "active" if not is_paused else "paused",
            "current_day": 1,
            "days_remaining": total_days
        }
    
    # Parse started_at
    try:
        if isinstance(started_at, str):
            start_date = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        else:
            start_date = started_at
    except:
        start_date = datetime.now(timezone.utc)
    
    # Calculate days elapsed
    now = datetime.now(timezone.utc)
    days_elapsed = (now - start_date).days
    current_day = min(days_elapsed + 1, total_days)
    days_remaining = max(0, total_days - days_elapsed)
    
    # Determine status
    if is_completed or days_remaining <= 0:
        status = "completed"
    elif is_paused:
        status = "paused"
    else:
        status = "active"
    
    return {
        "status": status,
        "current_day": current_day,
        "days_remaining": days_remaining
    }


def _get_jobs_applied_today(user_id: str, campaign_id: str) -> int:
    """Count jobs applied today for a campaign."""
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Get runs from today
    runs = db.client.table("campaign_runs").select("jobs_applied").eq(
        "agent_state_id", campaign_id
    ).gte("started_at", today).execute()
    
    return sum(r.get("jobs_applied", 0) for r in runs.data or [])


@router.post("/", response_model=CampaignResponse)
async def create_campaign(campaign: CampaignCreate):
    """Create a new job search campaign."""
    # Verify profile exists
    profile = db.get_profile(campaign.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create profile first.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create agent state (campaign)
    state = db.create_agent_state(
        user_id=campaign.user_id,
        config={
            "name": campaign.name,
            "job_titles": campaign.job_titles,
            "locations": campaign.locations,
            "keywords": campaign.keywords,
            "excluded_companies": campaign.excluded_companies,
            "total_days": campaign.total_days,
            "jobs_per_day": campaign.jobs_per_day,
            "auto_apply": campaign.auto_apply,
            "started_at": now,
            "created_at": now,
            "paused": False,
            "completed": False
        }
    )
    
    return {
        "id": state["id"],
        "user_id": campaign.user_id,
        "name": campaign.name,
        "status": "active",
        "config": state["config"],
        "created_at": state["created_at"],
        "current_day": 1,
        "days_remaining": campaign.total_days,
        "jobs_applied_today": 0
    }


@router.get("/user/{user_id}", response_model=List[CampaignResponse])
async def list_user_campaigns(user_id: str):
    """List all campaigns for a user."""
    states = db.get_agent_states(user_id)
    campaigns = []
    
    for s in states:
        config = s["config"]
        status_info = _calculate_campaign_status(config)
        jobs_today = _get_jobs_applied_today(user_id, s["id"])
        
        campaigns.append({
            "id": s["id"],
            "user_id": s["user_id"],
            "name": config.get("name", "Unnamed Campaign"),
            "status": status_info["status"],
            "config": config,
            "created_at": s["created_at"],
            "current_day": status_info["current_day"],
            "days_remaining": status_info["days_remaining"],
            "jobs_applied_today": jobs_today
        })
    
    return campaigns


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get campaign details."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    status_info = _calculate_campaign_status(config)
    jobs_today = _get_jobs_applied_today(state["user_id"], campaign_id)
    
    return {
        "id": state["id"],
        "user_id": state["user_id"],
        "name": config.get("name", "Unnamed"),
        "status": status_info["status"],
        "config": config,
        "thought_signature": state.get("thought_signature"),
        "last_run": state.get("updated_at"),
        "current_day": status_info["current_day"],
        "days_remaining": status_info["days_remaining"],
        "jobs_applied_today": jobs_today,
        "stats": await _get_campaign_stats(campaign_id)
    }


@router.post("/{campaign_id}/run", response_model=CampaignRunResponse)
async def run_campaign(campaign_id: str, background_tasks: BackgroundTasks):
    """
    Start a campaign run (job search).
    Runs in background and returns immediately.
    """
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    status_info = _calculate_campaign_status(config)
    
    # Check if campaign is completed/expired
    if status_info["status"] == "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Campaign has ended. Ran for {config.get('total_days', 7)} days."
        )
    
    # Check if campaign is paused
    if status_info["status"] == "paused":
        raise HTTPException(status_code=400, detail="Campaign is paused. Resume it first.")
    
    # Check daily job limit
    jobs_today = _get_jobs_applied_today(state["user_id"], campaign_id)
    jobs_per_day = config.get("jobs_per_day", 5)
    
    if jobs_today >= jobs_per_day:
        raise HTTPException(
            status_code=400, 
            detail=f"Daily limit reached ({jobs_today}/{jobs_per_day} jobs). Try again tomorrow."
        )
    
    # Calculate remaining jobs allowed today
    remaining_today = jobs_per_day - jobs_today
    
    # Create campaign run record
    run = db.create_campaign_run(
        user_id=state["user_id"],
        agent_state_id=campaign_id,
        run_type="search"
    )
    
    # Start background task with remaining limit
    background_tasks.add_task(_execute_campaign_run, campaign_id, run["id"], remaining_today)
    
    return {
        "id": run["id"],
        "campaign_id": campaign_id,
        "status": "started",
        "message": f"Campaign run started. Day {status_info['current_day']}/{config.get('total_days', 7)}, {remaining_today} jobs remaining today."
    }


@router.get("/{campaign_id}/runs")
async def get_campaign_runs(campaign_id: str, limit: int = 10):
    """Get recent campaign runs."""
    runs = db.client.table("campaign_runs").select("*").eq(
        "agent_state_id", campaign_id
    ).order("started_at", desc=True).limit(limit).execute()
    
    return runs.data


@router.patch("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    config["paused"] = True
    db.client.table("agent_states").update({"config": config}).eq("id", campaign_id).execute()
    
    return {"status": "paused"}


@router.patch("/{campaign_id}/resume")
async def resume_campaign(campaign_id: str):
    """Resume a paused campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    config["paused"] = False
    db.client.table("agent_states").update({"config": config}).eq("id", campaign_id).execute()
    
    return {"status": "active"}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """Delete a campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    db.client.table("agent_states").delete().eq("id", campaign_id).execute()
    return {"status": "deleted"}


async def _get_campaign_stats(campaign_id: str) -> Dict:
    """Get statistics for a campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        return {}
    
    # Get job applications for this campaign
    apps = db.client.table("job_applications").select("status").eq(
        "user_id", state["user_id"]
    ).execute()
    
    stats = {
        "total_jobs": len(apps.data),
        "by_status": {}
    }
    
    for app in apps.data:
        status = app.get("status", "unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
    
    return stats


async def _execute_campaign_run(campaign_id: str, run_id: str, max_jobs_today: int = 5):
    """Execute a campaign run in background."""
    try:
        state = db.get_agent_state(campaign_id)
        profile = db.get_profile(state["user_id"])
        
        # Initialize job search agent
        agent = JobSearchAgent(profile=profile)
        
        # Build search query from config
        config = state["config"]
        job_titles = config.get("job_titles", ["software engineer"])
        locations = config.get("locations", ["remote"])
        keywords = config.get("keywords", [])
        
        query = f"{' OR '.join(job_titles)} {' '.join(keywords)} {' OR '.join(locations)}"
        
        # Limit jobs to minimum of max_jobs_per_run and remaining daily quota
        max_jobs = max_jobs_today
        
        # --- 1. Search Local Public Job Listings (7 days) ---
        local_jobs_raw = db.get_recent_public_job_listings(days=7)
        local_jobs = []
        
        print(f"🔎 Found {len(local_jobs_raw)} local public jobs. Filtering...")
        
        for job in local_jobs_raw:
            # Map to application schema
            mapped_job = {
                "company": job.get("company") or "Unknown",
                "job_title": job.get("title") or "Unknown",
                "location": job.get("location") or "Unknown",
                "job_url": job.get("source_url"),
                "salary_range": "Unknown",
                "posted_date": job.get("created_at"),
                "job_description": job.get("description") or "",
                "application_email": job.get("contact_email"), # CRITICAL
                "match_score": 85, # Default high score for curated local jobs
                "source": "public_db"
            }
            
            # Simple keyword filtering
            # Match ANY job title in config
            title_match = False
            j_title = mapped_job["job_title"].lower()
            if not job_titles:
                title_match = True
            else:
                for t in job_titles:
                    if t.lower() in j_title:
                        title_match = True
                        break
            
            # Match ANY location in config
            loc_match = False
            j_loc = mapped_job["location"].lower()
            if not locations:
                loc_match = True
            else:
                for l in locations:
                    l_lower = l.lower()
                    if l_lower == "remote" and "remote" in j_loc:
                        loc_match = True
                    elif l_lower in j_loc:
                        loc_match = True
            
            if title_match and loc_match:
                local_jobs.append(mapped_job)
        
        print(f"   Matched {len(local_jobs)} local jobs.")

        # --- 2. Run AI Search ---
        # Adjust max_jobs for AI (giving priority to local jobs, but still fetching some AI jobs if needed)
        # If we have enough local jobs to fill the daily quota, we might skip AI or fetch fewer?
        # Let's fetch AI jobs to fill the gap or at least try to find some fresh ones.
        ai_jobs_count = max(0, max_jobs - len(local_jobs))
        ai_jobs = []
        if ai_jobs_count > 0:
            ai_jobs = agent.search(query, num_jobs=ai_jobs_count)
        
        # Merge lists (Local first)
        all_jobs = local_jobs + ai_jobs
        
        # --- 3. Deduplicate ---
        existing_keys = db.get_applied_job_keys(state["user_id"])
        jobs = []
        
        for j in all_jobs:
            # Generate key: company|title
            key = f"{(j.get('company') or '').lower().strip()}|{(j.get('job_title') or '').lower().strip()}"
            if key not in existing_keys:
                jobs.append(j)
                existing_keys.add(key) # Prevent internal duplicates in this run
        
        # Cap at max_jobs ensure we don't exceed daily limit
        jobs = jobs[:max_jobs]

        jobs_found = len(jobs)
        jobs_applied = 0
        summary = f"Found {jobs_found} jobs."

        # Check Gmail connection
        gmail_tokens = db.get_gmail_tokens(state["user_id"])

        for job in jobs:
            # Create job application as 'scouted'
            job_app = db.create_job_application(state["user_id"], job, status="scouted")
            job_id = job_app["id"] if job_app else None
            if gmail_tokens and job_id:
                try:
                    # Tailor resume and cover letter
                    from ..services.resume_tailor import ResumeTailorService
                    tailor_service = ResumeTailorService()
                    jd = job_app.get("job_description") or job_app.get("jd_analysis", {}).get("raw_jd", "")
                    profile_text = profile.get("raw_resume_text", "")
                    if not profile_text and profile.get("resume_data"):
                        profile_text = str(profile["resume_data"])
                    if jd and profile_text:
                        jd_analysis = await tailor_service.analyze_job_description(jd)
                        tailored = await tailor_service.tailor_resume_for_job(profile_text, jd)
                        cover_email = await tailor_service.generate_cover_email(profile_text, jd, profile.get("full_name", "Applicant"))
                        db.update_job_application(job_id, {
                            "status": "tailored",
                            "jd_analysis": jd_analysis,
                            "tailored_resume": tailored.get("final_resume"),
                            "cover_letter": cover_email
                        })
                        # Generate PDF
                        from ..services.pdf_renderer import generate_resume_pdf, convert_tailored_to_pdf_data
                        pdf_data = convert_tailored_to_pdf_data(tailored.get("final_resume"), profile)
                        output_path = f"resumes/{state['user_id']}/resume_job_{job_id}.pdf"
                        result_path = generate_resume_pdf(pdf_data, output_path)
                        db.update_job_application(job_id, {"resume_pdf_path": result_path})
                        # Create Gmail draft
                        from ..services.gmail_service import GmailService
                        gmail = GmailService(gmail_tokens)
                        to_email = job_app.get("application_email") or job_app.get("company_email")
                        subject = f"Application for {job_app.get('job_title', '')} at {job_app.get('company_name', '')} - {profile.get('full_name', '')}"
                        body = cover_email
                        draft_id = gmail.create_draft(to=to_email, subject=subject, body=body, attachment_path=result_path)
                        db.update_job_application(job_id, {"gmail_draft_id": draft_id, "status": "drafted"})
                        jobs_applied += 1
                except Exception as e:
                    print(f"❌ Failed to auto-apply for job {job_id}: {e}")
                    # Leave as scouted if any step fails
            # If no Gmail, leave as scouted

        # Update campaign run
        db.update_campaign_run(
            run_id=run_id,
            status="completed",
            jobs_found=jobs_found,
            jobs_applied=jobs_applied,
            summary=summary
        )
        
        # Check if campaign should be marked as completed (last day and done)
        status_info = _calculate_campaign_status(config)
        if status_info["days_remaining"] <= 0:
            config["completed"] = True
            db.client.table("agent_states").update({"config": config}).eq("id", campaign_id).execute()
            print(f"📅 Campaign {campaign_id} marked as completed (all days finished)")
        
        print(f"✅ Campaign run {run_id} completed: {jobs_found} jobs found, {jobs_applied} applied")
        
    except Exception as e:
        print(f"❌ Campaign run {run_id} failed: {e}")
        db.update_campaign_run(run_id=run_id, status="failed", summary=str(e))
