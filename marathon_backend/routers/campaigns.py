"""
Campaigns Router - Job search campaign management endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime, timezone

from ..models.database import MarathonDB
from ..models.schemas import CampaignCreate, CampaignResponse, CampaignRunResponse
from ..services.job_search import JobSearchAgent

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])
db = MarathonDB()


@router.post("/", response_model=CampaignResponse)
async def create_campaign(campaign: CampaignCreate):
    """Create a new job search campaign."""
    # Verify profile exists
    profile = db.get_profile(campaign.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create profile first.")
    
    # Create agent state (campaign)
    state = db.create_agent_state(
        user_id=campaign.user_id,
        config={
            "name": campaign.name,
            "job_titles": campaign.job_titles,
            "locations": campaign.locations,
            "keywords": campaign.keywords,
            "excluded_companies": campaign.excluded_companies,
            "max_jobs_per_run": campaign.max_jobs_per_run,
            "auto_apply": campaign.auto_apply,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    return {
        "id": state["id"],
        "user_id": campaign.user_id,
        "name": campaign.name,
        "status": "active",
        "config": state["config"],
        "created_at": state["created_at"]
    }


@router.get("/user/{user_id}", response_model=List[CampaignResponse])
async def list_user_campaigns(user_id: str):
    """List all campaigns for a user."""
    states = db.get_agent_states(user_id)
    return [
        {
            "id": s["id"],
            "user_id": s["user_id"],
            "name": s["config"].get("name", "Unnamed Campaign"),
            "status": "active" if not s["config"].get("paused") else "paused",
            "config": s["config"],
            "created_at": s["created_at"]
        }
        for s in states
    ]


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int):
    """Get campaign details."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "id": state["id"],
        "user_id": state["user_id"],
        "name": state["config"].get("name", "Unnamed"),
        "config": state["config"],
        "thought_signature": state.get("thought_signature"),
        "last_run": state.get("updated_at"),
        "stats": await _get_campaign_stats(campaign_id)
    }


@router.post("/{campaign_id}/run", response_model=CampaignRunResponse)
async def run_campaign(campaign_id: int, background_tasks: BackgroundTasks):
    """
    Start a campaign run (job search).
    Runs in background and returns immediately.
    """
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Create campaign run record
    run = db.create_campaign_run(
        user_id=state["user_id"],
        agent_state_id=campaign_id,
        run_type="search"
    )
    
    # Start background task
    background_tasks.add_task(_execute_campaign_run, campaign_id, run["id"])
    
    return {
        "run_id": run["id"],
        "campaign_id": campaign_id,
        "status": "started",
        "message": "Campaign run started in background"
    }


@router.get("/{campaign_id}/runs")
async def get_campaign_runs(campaign_id: int, limit: int = 10):
    """Get recent campaign runs."""
    runs = db.client.table("campaign_runs").select("*").eq(
        "agent_state_id", campaign_id
    ).order("started_at", desc=True).limit(limit).execute()
    
    return runs.data


@router.patch("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    """Pause a campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    config["paused"] = True
    db.client.table("agent_states").update({"config": config}).eq("id", campaign_id).execute()
    
    return {"status": "paused"}


@router.patch("/{campaign_id}/resume")
async def resume_campaign(campaign_id: int):
    """Resume a paused campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    config = state["config"]
    config["paused"] = False
    db.client.table("agent_states").update({"config": config}).eq("id", campaign_id).execute()
    
    return {"status": "active"}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int):
    """Delete a campaign."""
    state = db.get_agent_state(campaign_id)
    if not state:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    db.client.table("agent_states").delete().eq("id", campaign_id).execute()
    return {"status": "deleted"}


async def _get_campaign_stats(campaign_id: int) -> Dict:
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


async def _execute_campaign_run(campaign_id: int, run_id: int):
    """Execute a campaign run in background."""
    try:
        state = db.get_agent_state(campaign_id)
        profile = db.get_profile(state["user_id"])
        
        # Initialize job search agent
        agent = JobSearchAgent(
            user_id=state["user_id"],
            campaign_id=campaign_id
        )
        
        # Build search query from config
        config = state["config"]
        job_titles = config.get("job_titles", ["software engineer"])
        locations = config.get("locations", ["remote"])
        keywords = config.get("keywords", [])
        
        query = f"{' OR '.join(job_titles)} {' '.join(keywords)} {' OR '.join(locations)}"
        
        # Run search
        result = await agent.search_jobs(query, max_results=config.get("max_jobs_per_run", 10))
        
        # Update campaign run
        db.update_campaign_run(
            run_id=run_id,
            status="completed",
            jobs_found=result.get("jobs_found", 0),
            jobs_applied=result.get("jobs_applied", 0),
            summary=result.get("summary", "")
        )
        
        print(f"✅ Campaign run {run_id} completed: {result.get('jobs_found', 0)} jobs found")
        
    except Exception as e:
        print(f"❌ Campaign run {run_id} failed: {e}")
        db.update_campaign_run(run_id=run_id, status="failed", summary=str(e))
