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
from socketio import AsyncServer
from socketio.asgi import ASGIApp

# Load environment variables
load_dotenv()

# Import routers
# Import routers
from .routers import profile, profiles, campaigns, jobs, gmail, auth
from .services import socketio_service

# Socket.IO setup for real-time communication (must be before lifespan)
sio = AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*'],
    ping_timeout=60,
    ping_interval=25,
    engineio_logger=False,
    logger=True
)

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Marathon Backend starting...")
    
    # Create necessary directories
    Path("resumes").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize Socket.IO service
    socketio_service.initialize_socketio(sio)
    print("✅ Socket.IO initialized")
    
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
_fastapi_app = FastAPI(
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
_fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    query_string = environ.get('QUERY_STRING', '')
    user_id = 'unknown'
    if 'userId=' in query_string:
        user_id = query_string.split('userId=')[1].split('&')[0]
    print(f"✅ Socket.IO Client connected: {sid} (user: {user_id})")
    print(f"   QUERY_STRING: {query_string}")
    print(f"   PATH_INFO: {environ.get('PATH_INFO', 'N/A')}")
    await sio.emit('response', {'data': 'Connected to Marathon Backend', 'sid': sid}, to=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"❌ Socket.IO Client disconnected: {sid}")

@sio.on('subscribe_gmail')
async def subscribe_gmail_updates(sid, data):
    """Subscribe to Gmail updates for a user."""
    user_id = data.get('user_id') if data else 'unknown'
    print(f"📧 User {user_id} subscribed to Gmail updates (sid: {sid})")
    await sio.emit('gmail_subscribed', {'user_id': user_id, 'message': 'Subscribed to Gmail updates'}, to=sid)


# Global exception handler
@_fastapi_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


# Include routers
_fastapi_app.include_router(auth.router)
_fastapi_app.include_router(profile.router)
_fastapi_app.include_router(profiles.router)
_fastapi_app.include_router(campaigns.router)
_fastapi_app.include_router(jobs.router)
_fastapi_app.include_router(gmail.router)


# Health check endpoint
@_fastapi_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "marathon-backend",
        "version": "2.0.0"
    }


# Root endpoint
@_fastapi_app.get("/")
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
    _fastapi_app.mount("/resumes", StaticFiles(directory="resumes"), name="resumes")
except:
    pass  # Directory may not exist yet


# Create ASGI app that wraps FastAPI with Socket.IO
# This BECOMES THE MAIN APP when running with uvicorn
app = ASGIApp(sio, _fastapi_app)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "marathon_backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
