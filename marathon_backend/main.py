"""
Marathon Backend - FastAPI Application Entry Point

Unified backend for:
- Job search campaigns with thought signature persistence
- Resume tailoring with multi-agent pipeline
- Gmail integration for drafts and monitoring
- GitHub portfolio syncing
- PDF resume generation
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from .routers import profile, campaigns, jobs, gmail


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Marathon Backend starting...")
    
    # Create necessary directories
    Path("resumes").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Verify required env vars
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"⚠️ Missing env vars: {missing}")
    else:
        print("✅ Environment configured")
    
    yield
    
    # Shutdown
    print("👋 Marathon Backend shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Marathon Job Agent API",
    description="""
    AI-powered job search and application agent with:
    - Automated job search with Google grounding
    - Resume tailoring using recruiter/writer/critic agents
    - Gmail integration for application drafts
    - GitHub portfolio sync
    - Thought signature persistence for continuous learning
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


# Include routers
app.include_router(profile.router)
app.include_router(campaigns.router)
app.include_router(jobs.router)
app.include_router(gmail.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "marathon-backend",
        "version": "2.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """API root with endpoint summary."""
    return {
        "name": "Marathon Job Agent API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "profile": {
                "GET /api/profile/{user_id}": "Get user profile",
                "POST /api/profile/{user_id}": "Create/update profile",
                "POST /api/profile/{user_id}/resume/upload": "Upload resume PDF",
                "POST /api/profile/{user_id}/github/sync": "Sync GitHub portfolio"
            },
            "campaigns": {
                "POST /api/campaigns/": "Create job search campaign",
                "GET /api/campaigns/user/{user_id}": "List user campaigns",
                "GET /api/campaigns/{id}": "Get campaign details",
                "POST /api/campaigns/{id}/run": "Start campaign run",
                "PATCH /api/campaigns/{id}/pause": "Pause campaign",
                "PATCH /api/campaigns/{id}/resume": "Resume campaign"
            },
            "jobs": {
                "GET /api/jobs/user/{user_id}": "List job applications",
                "GET /api/jobs/{id}": "Get job details",
                "POST /api/jobs/{id}/tailor": "Tailor resume for job",
                "POST /api/jobs/{id}/generate-pdf": "Generate PDF resume",
                "POST /api/jobs/{id}/create-draft": "Create Gmail draft",
                "POST /api/jobs/{id}/send": "Send application"
            },
            "gmail": {
                "GET /api/gmail/auth?user_id=X": "Start OAuth flow",
                "GET /api/gmail/callback": "OAuth callback",
                "GET /api/gmail/status/{user_id}": "Check connection",
                "GET /api/gmail/inbox/{user_id}": "Check inbox",
                "GET /api/gmail/job-responses/{user_id}": "Check job responses"
            }
        }
    }


# Mount static files for resume downloads
try:
    app.mount("/resumes", StaticFiles(directory="resumes"), name="resumes")
except:
    pass  # Directory may not exist yet


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "marathon_backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
