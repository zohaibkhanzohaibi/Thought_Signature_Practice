"""
Profile Router - User profile management endpoints.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Optional
import os

from ..models.database import MarathonDB
from ..models.schemas import ProfileBase, ProfileResponse
from ..services.resume_parser import parse_resume_bytes
from ..services.github_service import GitHubService

router = APIRouter(prefix="/api/profile", tags=["Profile"])
db = MarathonDB()


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """Get user profile by ID."""
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/{user_id}", response_model=ProfileResponse)
async def create_or_update_profile(user_id: str, profile: ProfileBase):
    """Create or update user profile."""
    existing = db.get_profile(user_id)
    
    if existing:
        # Update existing
        update_data = profile.model_dump(exclude_unset=True)
        db.client.table("profiles").update(update_data).eq("id", user_id).execute()
        return db.get_profile(user_id)
    else:
        # Create new
        new_profile = {
            "id": user_id,
            **profile.model_dump(),
            "raw_resume_text": profile.resume_data or ""
        }
        db.client.table("profiles").insert(new_profile).execute()
        return db.get_profile(user_id)


@router.post("/{user_id}/resume/upload")
async def upload_resume(user_id: str, file: UploadFile = File(...)):
    """
    Upload and parse a resume PDF.
    Extracts structured data and updates profile.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    # Read file
    content = await file.read()
    
    # Parse with AI
    parsed = await parse_resume_bytes(content)
    
    # Update profile with parsed data
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create profile first.")
    
    update_data = {
        "resume_data": parsed,
        "raw_resume_text": parsed.get("raw_text", "")
    }
    
    # Also update contact info if available
    if parsed.get("name"):
        update_data["full_name"] = parsed["name"]
    if parsed.get("email"):
        update_data["email"] = parsed["email"]
    if parsed.get("phone"):
        update_data["phone"] = parsed["phone"]
    if parsed.get("linkedin"):
        update_data["linkedin_url"] = parsed["linkedin"]
    if parsed.get("github"):
        update_data["github_url"] = parsed["github"]
    
    db.client.table("profiles").update(update_data).eq("id", user_id).execute()
    
    return {
        "message": "Resume parsed and profile updated",
        "parsed_data": parsed
    }


@router.post("/{user_id}/github/sync")
async def sync_github(user_id: str, github_username: str = None):
    """
    Fetch GitHub portfolio data and update profile.
    Uses username from profile if not provided.
    """
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get username from param or profile URL
    username = github_username
    if not username and profile.get("github_url"):
        # Extract from URL like https://github.com/username
        parts = profile["github_url"].rstrip("/").split("/")
        if parts:
            username = parts[-1]
    
    if not username:
        raise HTTPException(
            status_code=400, 
            detail="GitHub username required. Provide username or set github_url in profile."
        )
    
    # Fetch GitHub data
    github_service = GitHubService()
    portfolio = await github_service.fetch_portfolio_data(username)
    
    # Update profile with GitHub portfolio
    update_data = {
        "github_portfolio": portfolio,
        "github_url": f"https://github.com/{username}"
    }
    
    db.client.table("profiles").update(update_data).eq("id", user_id).execute()
    
    return {
        "message": f"Synced {len(portfolio.get('repositories', []))} GitHub repositories",
        "portfolio": portfolio
    }


@router.get("/{user_id}/skills")
async def get_skills_summary(user_id: str):
    """Get aggregated skills from resume + GitHub."""
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    skills = set()
    
    # From resume
    resume_data = profile.get("resume_data", {})
    if isinstance(resume_data, dict) and resume_data.get("skills"):
        if isinstance(resume_data["skills"], list):
            skills.update(resume_data["skills"])
        else:
            skills.add(str(resume_data["skills"]))
    
    # From GitHub
    github_data = profile.get("github_portfolio", {})
    if github_data.get("languages"):
        skills.update(github_data["languages"])
    if github_data.get("technologies"):
        skills.update(github_data["technologies"])
    
    return {
        "skills": sorted(list(skills)),
        "sources": {
            "resume": bool(resume_data.get("skills")),
            "github": bool(github_data)
        }
    }
