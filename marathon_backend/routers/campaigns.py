from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
"""
Campaigns Router - Job search campaign management endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
import os
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
        
        similarity_threshold = 70  # Adjust as needed (0-100)
        now = datetime.now(timezone.utc)
        for job in local_jobs_raw:
            # Map to application schema
            mapped_job = {
                "company": job.get("company") or "Unknown",
                "job_title": job.get("title") or "Unknown",
                "location": job.get("location") or "Unknown",
                "job_url": job.get("source_url"),
                "salary_range": "Unknown",
                "posted_date": job.get("created_at"),
                "posted_date": job.get("created_at"),
                "job_description": job.get("description") or job.get("job_description") or "",
                "application_email": job.get("contact_email"), # CRITICAL
                "match_score": 85, # Default high score for curated local jobs
                "source": "public_db"
            }

            # Fuzzy job title matching (using difflib)
            best_score = 0
            best_title = None
            j_title = mapped_job["job_title"].lower()
            for t in job_titles:
                # Basic similarity ratio * 100 to match previous scale (0-100)
                matcher = SequenceMatcher(None, t.lower(), j_title)
                # usage of ratio() gives 0.0-1.0, so multiply by 100
                score = matcher.ratio() * 100
                # token_set_ratio is more forgiving, but ratio is a standard fallback
                # If we want 'contains' logic to boost score:
                if t.lower() in j_title:
                   score = max(score, 90) # Boost if direct substring match
                
                if score > best_score:
                    best_score = score
                    best_title = t

            # Location match (substring, as before)
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

            # Only add if similarity is above threshold, location matches, and job is recent
            created_at = mapped_job["posted_date"]
            try:
                created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else None
            except Exception:
                created_at_dt = None
            is_recent = created_at_dt and (now - created_at_dt) <= timedelta(days=7)

            if best_score >= similarity_threshold and loc_match and is_recent:
                mapped_job["similarity_score"] = best_score
                local_jobs.append(mapped_job)
        
        print(f"   Matched {len(local_jobs)} local jobs.")

        # --- 2. Run AI Search ---
        # ALWAYS run AI search to use Google Grounding as requested, unless max_jobs is very small.
        # We'll aim for at least 50% AI jobs or a minimum of 3.
        ai_jobs_target = max(3, max_jobs // 2)
        # But cap at max_jobs total if tight
        ai_jobs_target = min(ai_jobs_target, max_jobs)
        
        # Or simply: fetch a batch of fresh jobs to ensure grounding is used.
        # Let's fetch 'ai_jobs_target' jobs.
        
        print(f"🤖 Searching AI for {ai_jobs_target} fresh jobs via Google Grounding...")
        ai_jobs = []
        try:
             ai_jobs = agent.search(query, num_jobs=ai_jobs_target)
             print(f"   AI found {len(ai_jobs)} jobs.")
        except Exception as e:
            print(f"❌ AI Search failed: {e}")
        
        # Merge lists (Local + AI)
        # We prioritize AI jobs if they are fresh? Or mix them?
        # Let's put AI jobs first to ensure they are seen if we truncate.
        all_jobs = ai_jobs + local_jobs
        
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
            job_app = db.create_job_application(state["user_id"], job, status="scouted", campaign_id=campaign_id)
            job_id = job_app["id"] if job_app else None
            job_id = job_app["id"] if job_app else None
            
            # Start tailoring process if job was created
            if job_id:
                try:
                    # Initialize tailoring service with profile
                    from ..services.resume_tailor import ResumeTailorService
                    
                    # Get JD and Profile text
                    jd = job_app.get("job_description") or job_app.get("jd_analysis", {}).get("raw_jd", "")
                    
                    # Fallback if JD is empty (to unblock resume generation)
                    if not jd:
                        jd = f"Role: {job_app.get('job_title', 'Unknown Role')}\nCompany: {job_app.get('company_name', 'Unknown Company')}\nPlease refer to the job URL for full details."
                        # Optionally update the DB with this placeholder so it persists
                        db.update_job_application(job_id, {"job_description": jd})

                    # Build profile text from available fields if resume is missing
                    profile_text = ""
                    if profile.get("parsed_resume"):
                        profile_text = str(profile["parsed_resume"])
                    elif profile.get("summary"):
                        profile_text = profile["summary"]
                    
                    if len(profile_text) < 100:
                        meta_parts = []
                        if profile.get("skills"):
                            meta_parts.append(f"Skills: {', '.join(profile['skills'])}")
                        if profile.get("experience_years"):
                            meta_parts.append(f"Experience: {profile['experience_years']} years")
                        if profile.get("target_roles"):
                            meta_parts.append(f"Target Roles: {', '.join(profile['target_roles'])}")
                        profile_text = f"{profile_text}\n\nCandidate Metadata:\n" + "\n".join(meta_parts)

                    # Inject constructed text into profile for service
                    if not profile.get("parsed_resume"):
                        profile["parsed_resume"] = {"summary": profile_text}

                    tailor_service = ResumeTailorService(profile=profile)

                    # Only proceed if we have both JD and Profile text
                    if jd and len(profile_text.strip()) > 10:
                        # 1. Analyze and Tailor
                        jd_analysis = await tailor_service.analyze_jd(jd)
                        _, tailored_resume, _ = await tailor_service.tailor(jd)
                        cover_email = await tailor_service.generate_email(jd_analysis, tailored_resume)
                        
                        db.update_job_application(job_id, {
                            "status": "tailored",
                            "jd_analysis": jd_analysis,
                            "tailored_resume": tailored_resume,
                            "cover_letter": cover_email
                        })
                        
                        # 2. Generate PDF
                        from ..services.pdf_renderer import generate_resume_pdf, convert_tailored_to_pdf_data
                        pdf_data = convert_tailored_to_pdf_data(tailored_resume, profile)
                        
                        # Ensure directory exists
                        output_dir = f"resumes/{state['user_id']}"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        output_path = f"{output_dir}/resume_job_{job_id}.pdf"
                        result_path = generate_resume_pdf(pdf_data, output_path)
                        db.update_job_application(job_id, {"resume_pdf_path": result_path})
                        
                        # 3. Create Gmail draft (Strictly Conditional)
                        to_email = job_app.get("application_email") or job_app.get("company_email")
                        auto_apply = config.get("auto_apply", False)
                        
                        print(f"DEBUG: Job {job_id} - to_email: {to_email}, auto_apply: {auto_apply}, has_tokens: {gmail_tokens is not None}")
                        
                        if auto_apply and to_email and gmail_tokens:
                            from ..services.gmail_service import GmailService
                            gmail = GmailService(gmail_tokens)
                            subject = f"Application for {job_app.get('job_title', '')} at {job_app.get('company_name', '')} - {profile.get('full_name', '')}"
                            body = cover_email
                            
                            try:
                                draft_id = gmail.create_draft(to=to_email, subject=subject, body=body, attachment_path=result_path)
                                db.update_job_application(job_id, {"gmail_draft_id": draft_id, "status": "drafted"})
                                jobs_applied += 1
                                print(f"📧 Draft created for {job_id}")
                                
                                # Save updated tokens to keep session alive during long runs
                                db.save_gmail_tokens(
                                    user_id=state["user_id"],
                                    email=gmail.email_address,
                                    tokens=gmail.get_updated_tokens()
                                )
                            except Exception as e:
                                print(f"⚠️ Failed to create draft: {e}")
                            
                        elif not auto_apply:
                            print(f"ℹ️ Auto-apply disabled for {job_id}. Skipping draft.")
                            jobs_applied += 1
                        elif not to_email:
                            print(f"ℹ️ Job {job_id} has no email address. Skipping draft.")
                            jobs_applied += 1
                        elif not gmail_tokens:
                            print(f"⚠️ Gmail not connected for {state['user_id']}. Skipping draft.")
                            jobs_applied += 1
                    else:
                        reason = "Missing JD" if not jd else "Missing Resume Text in Profile"
                        print(f"⚠️ Skipping automation for job {job_id}: {reason}")

                except Exception as e:
                    print(f"❌ Failed to process job {job_id}: {e}")
                    # Leave as scouted if any step fails

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
