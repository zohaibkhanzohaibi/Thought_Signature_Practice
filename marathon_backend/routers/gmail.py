from pydantic import BaseModel
# Request model for sending email
class SendEmailRequest(BaseModel):
    user_id: str
    to: str
    subject: str
    body: str

"""
Gmail Router - Gmail OAuth and inbox monitoring endpoints.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import Dict, List, Optional

from ..models.database import MarathonDB
from ..services.gmail_service import GmailService

router = APIRouter(prefix="/api/gmail", tags=["Gmail"])
db = MarathonDB()


@router.get("/auth")
async def start_auth(user_id: str = Query(..., description="User ID to associate with Gmail")):
    """
    Start Gmail OAuth flow.
    Redirects user to Google consent screen.
    """
    try:
        auth_url = GmailService.get_auth_url(state=user_id)
        return RedirectResponse(url=auth_url)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    Gmail OAuth callback endpoint.
    Google redirects here after user consent.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")
    
    user_id = state
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID (state) missing")
    
    try:
        # Exchange code for tokens
        tokens = GmailService.exchange_code(code)
        
        # Save tokens to database
        db.save_gmail_tokens(
            user_id=user_id,
            email=tokens["email_address"],
            tokens={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expiry": tokens["expiry"],
                "scopes": tokens["scopes"]
            }
        )
        
        return {
            "message": "Gmail connected successfully!",
            "email": tokens["email_address"],
            "user_id": user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


@router.get("/status/{user_id}")
async def check_gmail_status(user_id: str):
    """Check if user has connected Gmail."""
    tokens = db.get_gmail_tokens(user_id)
    
    if not tokens:
        return {
            "connected": False,
            "message": "Gmail not connected. Visit /api/gmail/auth?user_id={user_id} to connect."
        }
    
    # Try to validate tokens
    try:
        gmail = GmailService(tokens)
        return {
            "connected": True,
            "email": gmail.email_address,
            "message": "Gmail connected and working"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "message": "Token expired or invalid. Re-authenticate at /api/gmail/auth"
        }


@router.delete("/disconnect/{user_id}")
async def disconnect_gmail(user_id: str):
    """Disconnect Gmail (remove stored tokens)."""
    db.client.table("user_gmail_tokens").delete().eq("user_id", user_id).execute()
    return {"message": "Gmail disconnected"}


@router.get("/drafts/{user_id}")
async def list_drafts(user_id: str, limit: int = 10):
    """List Gmail drafts for a user, with parsed details."""
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    gmail = GmailService(tokens)
    draft_refs = gmail.list_drafts(max_results=limit)
    parsed_drafts = []
    for d in draft_refs:
        try:
            draft = gmail.get_draft(d["id"])
            msg = draft["message"]
            headers = {h['name']: h['value'] for h in msg["payload"].get("headers", [])}
            # Extract body (reuse _get_body from GmailService)
            body = gmail._get_body(msg["payload"])
            parsed_drafts.append({
                "id": d["id"],
                "subject": headers.get("Subject", ""),
                "to": headers.get("To", ""),
                "body": body,
                "timestamp": msg.get("internalDate", ""),
                "snippet": msg.get("snippet", "")
            })
        except Exception as e:
            print(f"Failed to parse draft {d['id']}: {e}")
    return {"drafts": parsed_drafts}


@router.get("/inbox/{user_id}")
async def check_inbox(
    user_id: str,
    query: str = "",
    unread_only: bool = False,
    limit: int = 10
):
    """
    Check inbox for new messages.
    
    Query examples:
    - "is:unread" - Unread messages
    - "from:recruiter" - Messages from recruiters
    - "subject:interview" - Messages about interviews
    """
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    
    label_ids = ["INBOX"]
    if unread_only:
        label_ids.append("UNREAD")
    
    messages = gmail.get_messages(query=query, label_ids=label_ids, max_results=limit)
    
    return {
        "count": len(messages),
        "messages": messages
    }


@router.get("/job-responses/{user_id}")
async def check_job_responses(user_id: str, hours: int = 24):
    """
    Check for job-related email responses.
    Looks for recruiter emails, interview invites, etc.
    """
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    responses = gmail.check_for_job_responses(since_hours=hours)
    
    # Track in email_threads table
    new_threads = []
    for msg in responses:
        existing = db.client.table("email_threads").select("id").eq(
            "thread_id", msg["thread_id"]
        ).execute()
        
        if not existing.data:
            thread_data = {
                "user_id": user_id,
                "thread_id": msg["thread_id"],
                "subject": msg["subject"],
                "last_message_id": msg["id"],
                "from_email": msg["from"],
                "snippet": msg["snippet"],
                "status": "new"
            }
            db.client.table("email_threads").insert(thread_data).execute()
            new_threads.append(msg)
    
    return {
        "total_found": len(responses),
        "new_threads": len(new_threads),
        "messages": responses
    }


@router.post("/reply/{user_id}")
async def create_reply_draft(
    user_id: str,
    thread_id: str,
    body: str,
    message_id: str = None
):
    """
    Create a reply draft in a thread.
    """
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    
    # Get original thread to find recipient
    messages = gmail.get_messages(query=f"rfc822msgid:{message_id}" if message_id else "", max_results=1)
    
    if not messages:
        raise HTTPException(status_code=404, detail="Original message not found")
    
    original = messages[0]
    
    # Create reply draft
    draft_id = gmail.create_draft(
        to=original["from"],
        subject=f"Re: {original['subject']}" if not original['subject'].startswith('Re:') else original['subject'],
        body=body,
        in_reply_to=original.get("message_id")
    )
    
    return {
        "draft_id": draft_id,
        "replying_to": original["from"],
        "subject": original["subject"]
    }


@router.post("/mark-read/{user_id}/{message_id}")
async def mark_as_read(user_id: str, message_id: str):
    """Mark a message as read."""
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    gmail.mark_as_read(message_id)
    
    return {"message": "Marked as read"}


@router.post("/label/{user_id}/{message_id}")
async def add_label(user_id: str, message_id: str, label: str):
    """Add a label to a message."""
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    gmail.add_label(message_id, label)
    
    return {"message": f"Label '{label}' added"}


# ============================================
# EMAIL REPLY AGENT ENDPOINTS
# ============================================

@router.post("/reply-agent/{user_id}/process")
async def process_emails_with_agent(user_id: str, max_emails: int = 5):
    """
    Run the email reply agent to process unread emails.
    Classifies job-related emails and creates draft replies.
    """
    from ..services.email_reply_agent import EmailReplyAgent
    
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    agent = EmailReplyAgent(user_id, tokens)
    results = []
    
    for _ in range(max_emails):
        result = agent.run_once()
        results.append(result)
        
        if result["status"] == "no_new_emails":
            break
    
    return {
        "processed": len([r for r in results if r["status"] == "processed"]),
        "drafts_created": len([r for r in results if r.get("draft_created")]),
        "results": results
    }


@router.post("/reply-agent/{user_id}/classify/{message_id}")
async def classify_single_email(user_id: str, message_id: str):
    """
    Classify a single email as job-related or not.
    """
    from ..services.email_reply_agent import process_single_email
    
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    
    # Get the email
    try:
        messages = gmail.get_messages(query=f"rfc822msgid:{message_id}", max_results=1)
        if not messages:
            # Try by Gmail message ID
            messages = [gmail._parse_message(
                gmail.service.users().messages().get(
                    userId='me', id=message_id, format='full'
                ).execute()
            )]
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Email not found: {e}")
    
    email = messages[0]
    result = await process_single_email(user_id, tokens, email)
    
    return result


@router.post("/reply-agent/{user_id}/generate-reply/{message_id}")
async def generate_reply_for_email(user_id: str, message_id: str, create_draft: bool = True):
    """
    Generate a reply for a specific email.
    Optionally creates a Gmail draft.
    """
    from ..services.email_reply_agent import EmailReplyAgent
    
    tokens = db.get_gmail_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    
    gmail = GmailService(tokens)
    
    # Get the email
    try:
        email = gmail._parse_message(
            gmail.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Email not found: {e}")
    
    # Process with agent
    agent = EmailReplyAgent(user_id, tokens)
    agent.state["initialized"] = True
    agent.state["new_email"] = email
    
    # Generate response
    agent.generate_response()
    reply_text = agent.state.get("llm_output", "")
    
    result = {
        "email_id": message_id,
        "subject": email.get("subject"),
        "from": email.get("from"),
        "generated_reply": reply_text
    }
    
    if create_draft and reply_text:
        agent.create_draft_response()
        result["draft_created"] = True
    
    return result

@router.post("/send")
async def send_email(request: SendEmailRequest):
    """Send email through Gmail (creates and sends a draft)."""
    tokens = db.get_gmail_tokens(request.user_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    gmail = GmailService(tokens)
    draft_id = gmail.create_draft(
        to=request.to,
        subject=request.subject,
        body=request.body
    )
    result = gmail.send_draft(draft_id)
    return {"success": True, "message_id": result.get("id")}
from fastapi import BackgroundTasks
# In-memory store for active monitors (for demonstration; use persistent store/actor for production)
active_monitors = {}

@router.post("/connect")
async def connect_gmail(user_id: str, token: dict, background_tasks: BackgroundTasks):
    """Connect to Gmail and start monitoring (placeholder, no real background thread)."""
    # In production, use a persistent background worker or actor system
    # Here, just store the token for the user
    active_monitors[user_id] = token
    # Optionally, start a background task for polling/monitoring
    # background_tasks.add_task(your_monitoring_function, user_id, token)
    return {"success": True, "message": "Gmail monitoring started"}

@router.post("/disconnect")
async def disconnect_gmail(user_id: str):
    """Disconnect Gmail monitoring (placeholder)."""
    if user_id in active_monitors:
        del active_monitors[user_id]
    return {"success": True}