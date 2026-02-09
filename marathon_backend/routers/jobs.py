"""
Jobs Router - Job applications and application workflow endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ..models.database import MarathonDB
from ..models.schemas import JobResponse, JobApplicationUpdate, GmailDraftCreate, JobManualExtractRequest
from ..services.resume_tailor import ResumeTailorService
from ..services.gmail_service import GmailService
from ..services.pdf_renderer import generate_resume_pdf, convert_tailored_to_pdf_data
from ..models.schemas import RawJobPost, PublicJobCreate, PublicJobResponse
from ..services.job_parser import parse_job_text
from .auth import get_current_user
from ..services.job_search import search_jobs_with_ai, get_job_key
from pydantic import BaseModel

class JobSearchRequest(BaseModel):
    query: str
    location: str = "Remote"
    num_jobs: int = 5
    days_limit: int = 7

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])
db = MarathonDB()


@router.get("/user/{user_id}", response_model=List[JobResponse])
async def list_jobs(
    user_id: str,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List job applications for a user.
    Optionally filter by status.
    """
    query = db.client.table("job_applications").select("*").eq("user_id", user_id)
    
    if status:
        query = query.eq("status", status)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        # Ensure 'company' is always a string for response validation
    for job in result.data:
        if job.get('company') is None:
            job['company'] = ""
    return result.data


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get job application details."""
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, update: JobApplicationUpdate):
    """Update job application status and details."""
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = update.model_dump(exclude_unset=True)
    db.client.table("job_applications").update(update_data).eq("id", job_id).execute()
    
    return db.get_job_application(job_id)


@router.post("/{job_id}/tailor")
async def tailor_resume_for_job(job_id: str, background_tasks: BackgroundTasks = None):
    """
    Tailor resume and generate cover email for a job.
    Uses the multi-agent pipeline (recruiter -> writer -> critic).
    """
    import logging
    logger = logging.getLogger("tailor_resume")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    if not logger.hasHandlers():
        logger.addHandler(handler)

    job = db.get_job_application(job_id)
    if not job:
        logger.error("Job not found for job_id=%s", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    
    profile = db.get_profile(job["user_id"])
    if not profile:
        logger.error("User profile not found for user_id=%s", job.get("user_id"))
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Get job description
    jd = job.get("job_description") or job.get("jd_analysis", {}).get("raw_jd", "")
    if not jd:
        logger.error("Job description missing for job_id=%s", job_id)
        raise HTTPException(
            status_code=400, 
            detail="Job description required. Update job with job_description first."
        )
    
    # Get resume data
    resume_text = profile.get("raw_resume_text", "")
    if not resume_text and profile.get("resume_data"):
        resume_text = str(profile["resume_data"])
    # Fallback: use parsed_resume if present
    if not resume_text and profile.get("parsed_resume"):
        parsed = profile["parsed_resume"]
        resume_text = parsed if isinstance(parsed, dict) else str(parsed)
    logger.debug("Resume text type: %s, value: %s", type(resume_text), str(resume_text)[:200])
    if not resume_text:
        logger.error("Resume not found for user_id=%s", job.get("user_id"))
        raise HTTPException(status_code=400, detail="Resume not found. Upload resume first.")
    
    # Run tailoring pipeline
    try:
        tailor_service = ResumeTailorService(profile=resume_text)
        logger.debug("Starting JD analysis")
        jd_analysis = await tailor_service.analyze_jd(jd)
        logger.debug("JD analysis complete")
        logger.debug("Starting resume tailoring")
        # Use the class's tailor method, which expects job_description and uses self.profile
        tailor_result = await tailor_service.tailor(jd)
        logger.debug("Resume tailoring complete")
        logger.debug("Starting cover email generation")
        # tailor returns (jd_analysis, tailored_resume, final_score)
        jd_analysis2, tailored_resume, final_score = tailor_result
        cover_email = await tailor_service.generate_email(jd_analysis=jd_analysis2, tailored_resume=tailored_resume)
        logger.debug("Cover email generation complete")
    except Exception as e:
        logger.exception("Error during tailoring pipeline: %s", e)
        raise HTTPException(status_code=500, detail=f"Tailoring pipeline failed: {e}")
    
    # Update job with tailored content
    update_data = {
        "status": "tailored",
        "jd_analysis": jd_analysis2,
        "tailored_resume": tailored_resume,
        "cover_letter": cover_email
    }
    db.client.table("job_applications").update(update_data).eq("id", job_id).execute()
    
    return {
        "message": "Resume tailored successfully",
        "jd_analysis": jd_analysis2,
        "tailored_resume": tailored_resume,
        "cover_email": cover_email,
        "final_score": final_score
    }


@router.post("/{job_id}/generate-pdf")
async def generate_pdf(job_id: str):
    """
    Generate a PDF resume from tailored content.
    """
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    tailored = job.get("tailored_resume")
    if not tailored:
        raise HTTPException(
            status_code=400, 
            detail="Resume not tailored yet. Call /tailor first."
        )
    
    profile = db.get_profile(job["user_id"])
    
    # Convert to PDF format
    if isinstance(tailored, str):
        # If it's just text, create basic structure
        pdf_data = {
            "name": profile.get("full_name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "linkedin": profile.get("linkedin_url", ""),
            "github": profile.get("github_url", ""),
            "summary": tailored[:500] if len(tailored) > 500 else tailored
        }
    else:
        pdf_data = convert_tailored_to_pdf_data(tailored, profile)
    
    # Generate PDF
    output_path = f"resumes/{job['user_id']}/resume_job_{job_id}.pdf"
    try:
        result_path = generate_resume_pdf(pdf_data, output_path)
        
        # Update job with PDF path
        db.client.table("job_applications").update({
            "resume_pdf_path": result_path
        }).eq("id", job_id).execute()
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=result_path, 
            filename=f"Resume_{job.get('company', 'Company')}_{job.get('job_title', 'Job')}.pdf",
            media_type='application/pdf'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/{job_id}/create-draft")
async def create_gmail_draft(job_id: str, draft: GmailDraftCreate = None):
    """
    Create a Gmail draft for this job application.
    Uses tailored cover letter as email body.
    """
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    profile = db.get_profile(job["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get Gmail tokens
    tokens = db.get_gmail_tokens(job["user_id"])
    if not tokens:
        raise HTTPException(
            status_code=400, 
            detail="Gmail not connected. Visit /api/gmail/auth to authenticate."
        )
    
    # Get or compute email content
    if draft:
        to_email = draft.to_email
        subject = draft.subject
        body = draft.body
    else:
        to_email = job.get("application_email") or job.get("contact_email")
        if not to_email:
            raise HTTPException(
                status_code=400, 
                detail="No recipient email. Provide to_email in request or update job with application_email."
            )
        
        company = job.get("company_name", "the company")
        title = job.get("job_title", "the position")
        
        subject = f"Application for {title} at {company} - {profile.get('full_name', '')}"
        body = job.get("cover_letter", "")
        
        if not body:
            raise HTTPException(
                status_code=400, 
                detail="Cover letter not generated. Call /tailor first."
            )
    
    # Create Gmail draft
    gmail = GmailService(tokens)
    
    attachment = job.get("resume_pdf_path")
    draft_id = gmail.create_draft(
        to=to_email,
        subject=subject,
        body=body,
        attachment_path=attachment
    )
    
    # Update job with draft info
    db.client.table("job_applications").update({
        "gmail_draft_id": draft_id,
        "status": "draft_created"
    }).eq("id", job_id).execute()
    
    # Update tokens in case they were refreshed
    db.save_gmail_tokens(
        user_id=job["user_id"],
        email=gmail.email_address,
        tokens=gmail.get_updated_tokens()
    )
    
    return {
        "message": "Gmail draft created",
        "draft_id": draft_id,
        "to": to_email,
        "subject": subject
    }


@router.post("/{job_id}/send")
async def send_application(job_id: str):
    """
    Send the Gmail draft for this job.
    """
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    draft_id = job.get("gmail_draft_id")
    if not draft_id:
        raise HTTPException(
            status_code=400, 
            detail="No draft created. Call /create-draft first."
        )
    
    tokens = db.get_gmail_tokens(job["user_id"])
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    result = gmail.send_draft(draft_id)
    
    # Update job status
    db.client.table("job_applications").update({
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", job_id).execute()
    
    return {
        "message": "Application sent!",
        "message_id": result.get("id")
    }


@router.get("/stats/{user_id}")
async def get_job_stats(user_id: str):
    """Get job application statistics for a user."""
    jobs = db.client.table("job_applications").select("status, created_at").eq(
        "user_id", user_id
    ).execute()
    
    stats = {
        "total": len(jobs.data),
        "by_status": {},
        "this_week": 0,
        "this_month": 0
    }
    
    now = datetime.now(timezone.utc)
    
    for job in jobs.data:
        status = job.get("status", "unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        created = job.get("created_at")
        if created:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            days_ago = (now - created_dt).days
            if days_ago <= 7:
                stats["this_week"] += 1
            if days_ago <= 30:
                stats["this_month"] += 1
    
    return stats

@router.post("/{job_id}/mark-applied")
async def mark_job_as_applied(job_id: str):
    """
    Mark a scouted job as manually applied by the user.
    Sets status to 'applied' and records applied_at timestamp.
    """
    job = db.get_job_application(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") not in ["scouted", "tailored", "drafted"]:
        raise HTTPException(status_code=400, detail="Job is not in a state that can be marked as applied")
    db.client.table("job_applications").update({
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", job_id).execute()
    return {"message": "Job marked as applied"}


# 1. Parse Endpoint
@router.post("/parse-raw")
async def analyze_raw_job(
    post: RawJobPost, 
    user = Depends(get_current_user) # <--- Auth Guard
):
    # We don't strictly need the user ID for parsing, but this protects the API
    # so only logged-in users can use your AI quota.
    extracted_data = await parse_job_text(post.raw_text)
    return extracted_data

# 2. Public Job Endpoint
@router.post("/public", response_model=PublicJobResponse)
async def post_public_job(
    job: PublicJobCreate, 
    user = Depends(get_current_user) # <--- Auth Guard returns the user
):
    # Prepare data for DB
    job_data = job.model_dump()
    
    # INJECT USER ID HERE
    job_data['original_poster_id'] = user["id"]
    
    res = db.client.table("public_job_listings").insert(job_data).execute()
    return res.data[0]

# 3. Endpoint to List Public Jobs
@router.get("/public/feed")
async def get_public_jobs(limit: int = 20):
    """Get the feed of community sourced jobs."""
    res = db.client.table("public_job_listings").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data

# 4. Save to Profile Endpoint
@router.post("/public/{public_job_id}/save-to-profile")
async def save_public_job_to_profile(
    public_job_id: int, 
    user = Depends(get_current_user) # <--- Backend derives ID
):
    # Fetch public job
    pub_job = db.client.table("public_job_listings").select("*").eq("id", public_job_id).single().execute()
    data = pub_job.data
    
    new_app = {
        "user_id": user["id"],
        "job_title": data.get("title"),  # Use .get() for safety
        "company": data.get("company"),    # Changed from company_name to company to match schema
        "job_description": data.get("description"),
        "location": data.get("location"),
        "contact_email": data.get("contact_email"), # Changed to likely schema match
        "job_url": data.get("source_url"), # Changed from source_url to job_url
        "status": "scouted",
        "match_score": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    res = db.client.table("job_applications").insert(new_app).execute()
    return res.data[0]


@router.post("/search")
async def search_jobs(request: JobSearchRequest, user_id: str):
    """
    Smart Job Search:
    1. Search Google for new jobs (grounding).
    2. Save new findings to DB.
    3. Return mix of new + existing jobs from last 7 days.
    """
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # 1. Search for new jobs
    new_jobs, signature = search_jobs_with_ai(
        query=request.query,
        profile=profile,
        location=request.location,
        num_jobs=request.num_jobs
    )

    # 2. Save new unique jobs
    saved_jobs = []
    for job in new_jobs:
        # Check if exists
        existing = db.client.table("job_applications").select("id").eq("user_id", user_id).eq("job_url", job.get("job_url")).execute()
        
        if not existing.data:
            # Insert new
            job_data = {
                "user_id": user_id,
                "company": job.get("company"),
                "job_title": job.get("job_title"),
                "job_url": job.get("job_url"),
                "location": job.get("location"),
                "salary_range": job.get("salary_range"),
                "posted_date": job.get("posted_date"),
                "job_description": job.get("job_description"),
                "match_score": job.get("match_score"),
                "status": "scouted", # Using 'scouted' as 'discovered'
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            res = db.client.table("job_applications").insert(job_data).execute()
            if res.data:
                saved_jobs.append(res.data[0])
        else:
             # Already exists, maybe update? For now just skip
             pass

    # 3. Fetch all relevant jobs (New + Existing recent)
    # Calculate cutoff date
    cutoff = datetime.now(timezone.utc).timestamp() - (request.days_limit * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    # Query DB for jobs matching criteria
    # internal database search is simple for now, can be improved with full text search later
    
    # We will return the newly found jobs + any existing 'scouted' jobs for this query
    # A simple way is to just return what we have in DB that matches the 'scouted' status and recent time
    # ideally we filter by query too, but strict SQL matching on text is hard without FTS.
    # For now, let's return all 'scouted' jobs from last 7 days to populate the view
    
    recent_jobs = db.client.table("job_applications")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "scouted")\
        .gte("created_at", cutoff_iso)\
        .order("created_at", desc=True)\
        .execute()
        
    return recent_jobs.data
