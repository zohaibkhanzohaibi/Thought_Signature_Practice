"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# ENUMS
# ============================================

class JobStatus(str, Enum):
    SCOUTED = "scouted"
    ANALYZING = "analyzing"
    TAILORED = "tailored"
    DRAFTED = "drafted"
    SENT = "sent"
    REPLIED = "replied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ThreadStatus(str, Enum):
    PENDING = "pending"
    NEEDS_REPLY = "needs_reply"
    REPLIED = "replied"
    WAITING = "waiting"
    CLOSED = "closed"


# ============================================
# PROFILE SCHEMAS
# ============================================

class ProfileBase(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_username: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = []
    experience_years: Optional[int] = 0
    preferred_locations: Optional[List[str]] = []
    target_roles: Optional[List[str]] = []


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_username: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None


class ProfileResponse(ProfileBase):
    id: str
    parsed_resume: Optional[Dict] = {}
    portfolio_data: Optional[Dict] = {}
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# CAMPAIGN SCHEMAS
# ============================================

class CampaignCreate(BaseModel):
    user_id: str = Field(..., description="User ID for the campaign")
    name: str = Field(..., description="Campaign name")
    job_titles: List[str] = Field(default=["Software Engineer"], description="Target job titles")
    locations: List[str] = Field(default=["Remote"], description="Preferred locations")
    keywords: Optional[List[str]] = Field(default=[], description="Additional search keywords")
    excluded_companies: Optional[List[str]] = Field(default=[], description="Companies to avoid")
    total_days: int = Field(default=7, ge=1, le=90, description="Total days to run campaign")
    jobs_per_day: int = Field(default=5, ge=1, le=50, description="Max jobs to apply per day")
    auto_apply: bool = Field(default=False, description="Auto-create Gmail drafts")


class CampaignConfig(BaseModel):
    name: str
    job_titles: List[str] = []
    locations: List[str] = []
    keywords: List[str] = []
    excluded_companies: List[str] = []
    total_days: int = 7
    jobs_per_day: int = 5
    auto_apply: bool = False
    started_at: Optional[str] = None
    created_at: Optional[str] = None
    paused: bool = False
    completed: bool = False


class CampaignResponse(BaseModel):
    id: str
    user_id: str
    name: str
    status: str = "active"  # active, paused, completed, expired
    config: Dict[str, Any]
    created_at: Optional[datetime] = None
    current_day: Optional[int] = None
    days_remaining: Optional[int] = None
    jobs_applied_today: Optional[int] = None

    class Config:
        from_attributes = True


class CampaignRunResponse(BaseModel):
    id: str
    campaign_id: str
    status: str = "started"
    message: str = "Campaign run started"
    jobs_found: int = 0


class CampaignStatus(BaseModel):
    user_id: str
    user_name: str
    config: CampaignConfig
    total_jobs_scouted: int
    total_jobs_applied: int
    is_active: bool


# ============================================
# JOB SCHEMAS
# ============================================

class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    match_score: Optional[int] = 0


class JobCreate(JobBase):
    pass


class JobResponse(BaseModel):
    id: str
    user_id: str
    job_title: str
    company_name: str
    location: Optional[str] = None
    source_url: Optional[str] = None
    job_description: Optional[str] = None
    posted_date: Optional[str] = None
    match_score: Optional[int] = 0
    status: JobStatus
    jd_analysis: Optional[Dict] = {}
    tailored_resume: Optional[Dict] = {}
    cover_email: Optional[str] = None
    resume_pdf_path: Optional[str] = None
    gmail_draft_id: Optional[str] = None
    company_email: Optional[str] = None
    applied_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    replies_log: Optional[List[Dict]] = []

    class Config:
        from_attributes = True


class JobTailorRequest(BaseModel):
    job_description: Optional[str] = None  # If not already stored


class JobApplyRequest(BaseModel):
    recipient_email: EmailStr
    custom_subject: Optional[str] = None
    custom_message: Optional[str] = None


class JobStatusUpdate(BaseModel):
    status: JobStatus
    notes: Optional[str] = None


class JobApplicationUpdate(BaseModel):
    """Update job application fields."""
    status: Optional[JobStatus] = None
    jd_analysis: Optional[Dict[str, Any]] = None
    tailored_resume: Optional[Dict[str, Any]] = None
    cover_email: Optional[str] = None
    resume_pdf_path: Optional[str] = None
    gmail_draft_id: Optional[str] = None
    company_email: Optional[str] = None
    notes: Optional[str] = None


# ============================================
# JD ANALYSIS SCHEMAS
# ============================================

class JDAnalysis(BaseModel):
    company_name: str
    job_title: str
    hard_skills: List[str] = []
    soft_skills: List[str] = []
    culture_keywords: List[str] = []
    hidden_signals: List[str] = []
    company_email: Optional[str] = None


# ============================================
# RESUME SCHEMAS
# ============================================

class PersonalInfo(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


class Education(BaseModel):
    school: str
    location: Optional[str] = None
    degree: str
    dates: Optional[str] = None


class Experience(BaseModel):
    company: str
    location: Optional[str] = None
    role: str
    dates: Optional[str] = None
    bullets: List[str] = []


class Project(BaseModel):
    name: str
    tech_stack: Optional[str] = None
    dates: Optional[str] = None
    bullets: List[str] = []


class Skill(BaseModel):
    category: str
    values: str


class TailoredResume(BaseModel):
    personal_info: PersonalInfo
    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []
    skills: List[Skill] = []


# ============================================
# GMAIL SCHEMAS
# ============================================

class GmailAuthRequest(BaseModel):
    """OAuth callback data"""
    code: str
    state: Optional[str] = None


class GmailDraftCreate(BaseModel):
    to: EmailStr
    subject: str
    body: str
    attachment_path: Optional[str] = None


class EmailThreadResponse(BaseModel):
    id: str
    gmail_thread_id: str
    subject: Optional[str] = None
    last_sender: Optional[str] = None
    last_snippet: Optional[str] = None
    message_count: int = 1
    status: ThreadStatus
    is_job_related: bool = False
    job_application_id: Optional[str] = None
    auto_reply_draft_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailReplyRequest(BaseModel):
    custom_reply: Optional[str] = None  # If not provided, auto-generate


# ============================================
# CRON / SYSTEM SCHEMAS
# ============================================

class CronRunRequest(BaseModel):
    user_id: Optional[str] = None  # If None, run for all active campaigns
    dry_run: bool = False  # If True, don't actually apply


class CronRunResponse(BaseModel):
    run_id: str
    users_processed: int
    jobs_scouted: int
    jobs_tailored: int
    jobs_drafted: int
    emails_checked: int
    errors: List[str] = []
    status: str


class HealthResponse(BaseModel):
    status: str = "healthy"
    database: str = "connected"
    gemini_api: str = "available"
    version: str = "1.0.0"
