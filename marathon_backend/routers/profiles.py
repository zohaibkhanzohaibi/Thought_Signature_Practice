from fastapi import APIRouter, HTTPException
from ..models.database import MarathonDB

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])
db = MarathonDB()

@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    """Get public profile details."""
    profile = db.get_profile(user_id)
    
    if not profile:
        # If no profile exists, return a basic placeholder based on ID
        return {
            "id": user_id,
            "full_name": "Guest User", 
            "email": "",
            "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_id}"
        }
    
    return profile