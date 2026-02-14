"""
Profile Router - User profile management endpoints.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Optional
import os
import uuid

from ..models.database import MarathonDB
from ..models.schemas import ProfileBase, ProfileUpdate, ProfileResponse
from ..services.resume_parser import parse_resume_bytes
from ..services.github_service import GitHubService

router = APIRouter(prefix="/api/profile", tags=["Profile"])
db = MarathonDB()

# Namespace for generating consistent UUIDs from user_id strings
NAMESPACE_JOBFLOW = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def get_uuid_from_user_id(user_id: str) -> str:
    """Generate a consistent UUID from a user_id string."""
    # If it's already a valid UUID, return as-is
    try:
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        # Generate UUID5 from the string (deterministic)
        return str(uuid.uuid5(NAMESPACE_JOBFLOW, user_id))


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """Get user profile by ID."""
    uuid_id = get_uuid_from_user_id(user_id)
    profile = db.get_profile(uuid_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/{user_id}", response_model=ProfileResponse)
async def create_or_update_profile(user_id: str, profile: ProfileUpdate):
    """Create or update user profile. Partial updates supported."""
    uuid_id = get_uuid_from_user_id(user_id)
    existing = db.get_profile(uuid_id)
    
    update_data = profile.model_dump(exclude_unset=True, exclude_none=True)
    
    # Check if github_username is being updated
    github_changed = (
        'github_username' in update_data and 
        update_data['github_username'] and
        (not existing or existing.get('github_username') != update_data['github_username'])
    )
    
    if existing:
        # Update existing
        db.client.table("profiles").update(update_data).eq("id", uuid_id).execute()
    else:
        # Create new - ensure full_name exists
        if 'full_name' not in update_data:
            update_data['full_name'] = 'New User'
        new_profile = {
            "id": uuid_id,
            **update_data
        }
        db.client.table("profiles").insert(new_profile).execute()
    
    # Auto-sync GitHub if username changed
    if github_changed:
        try:
            github_service = GitHubService(username=update_data['github_username'])
            portfolio = github_service.fetch_portfolio()
            db.client.table("profiles").update({
                "portfolio_data": portfolio
            }).eq("id", uuid_id).execute()
        except Exception as e:
            print(f"GitHub sync failed: {e}")
    
    return db.get_profile(uuid_id)


@router.post("/{user_id}/resume/upload")
async def upload_resume(user_id: str, file: UploadFile = File(...)):
    """
    Upload and parse a resume PDF.
    Extracts structured data and updates profile.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    uuid_id = get_uuid_from_user_id(user_id)
    
    # Read file
    content = await file.read()
    
    # Parse with AI
    parsed = await parse_resume_bytes(content, file.filename)
    
    # Update profile with parsed data
    profile = db.get_profile(uuid_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create profile first.")
    
    update_data = {
        "parsed_resume": parsed,  # Use correct column name from DB schema
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
        update_data["github_username"] = parsed["github"]
    if parsed.get("skills"):
        update_data["skills"] = parsed["skills"]
    
    db.client.table("profiles").update(update_data).eq("id", uuid_id).execute()
    
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
    uuid_id = get_uuid_from_user_id(user_id)
    profile = db.get_profile(uuid_id)
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
    github_service = GitHubService(username=username)
    portfolio = github_service.fetch_portfolio()
    
    # Update profile with GitHub portfolio
    update_data = {
        "portfolio_data": portfolio,  # Use correct column name from DB schema
        "github_username": username
    }
    
    db.client.table("profiles").update(update_data).eq("id", uuid_id).execute()
    
    return {
        "message": f"Synced {len(portfolio.get('repositories', []))} GitHub repositories",
        "portfolio": portfolio
    }


@router.get("/{user_id}/skills")
async def get_skills_summary(user_id: str):
    """Get aggregated skills from resume + GitHub."""
    uuid_id = get_uuid_from_user_id(user_id)
    profile = db.get_profile(uuid_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    skills = set()
    
    # From profile skills array
    profile_skills = profile.get("skills", [])
    if profile_skills:
        skills.update(profile_skills)
    
    # From parsed resume
    resume_data = profile.get("parsed_resume", {})
    if isinstance(resume_data, dict) and resume_data.get("skills"):
        if isinstance(resume_data["skills"], list):
            skills.update(resume_data["skills"])
        else:
            skills.add(str(resume_data["skills"]))
    
    # From GitHub portfolio
    github_data = profile.get("portfolio_data", {})
    if isinstance(github_data, dict):
        if github_data.get("languages"):
            skills.update(github_data["languages"])
        if github_data.get("technologies"):
            skills.update(github_data["technologies"])
    
    return {
        "skills": sorted(list(skills)),
        "sources": {
            "resume": bool(resume_data.get("skills") if isinstance(resume_data, dict) else False),
            "github": bool(github_data)
        }
    }
