import requests
from pydantic import BaseModel
from ..models.schemas import GmailConnectRequest
from ..services import socketio_service

# Request model for sending email
class SendEmailRequest(BaseModel):
    user_id: str
    to: str
    subject: str
    body: str

"""
Gmail Router - Gmail OAuth and inbox monitoring endpoints.
"""
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from typing import Dict, List, Optional

from ..models.database import MarathonDB
from ..services.gmail_service import GmailService
from googleapiclient.errors import HttpError

router = APIRouter(prefix="/api/gmail", tags=["Gmail"])
db = MarathonDB()

active_monitors = {}

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
    """Check if user has connected Gmail (Checks DB first, then Memory)."""
    
    # 1. Try DB
    tokens = db.get_gmail_tokens(user_id)
    
    # 2. Try Memory (Fallback)
    if not tokens:
        tokens = active_monitors.get(user_id)
    
    if not tokens:
        return {
            "connected": False,
            "message": "Gmail not connected. Visit /api/gmail/auth?user_id={user_id} to connect."
        }
    
    # 3. Validate Connection
    try:
        # If it's a dict from memory, use it directly. If from DB object, might need conversion.
        # Assuming your GmailService handles dicts:
        gmail = GmailService(tokens)
        return {
            "connected": True,
            "email": gmail.email_address,
            "message": "Gmail connected and working"
        }
    except Exception as e:
        # If the token in memory is bad, clear it so we don't loop forever
        if user_id in active_monitors:
            del active_monitors[user_id]
            
        return {
            "connected": False,
            "error": str(e),
            "message": "Token expired or invalid. Re-authenticate at /api/gmail/auth"
        }


@router.delete("/disconnect/{user_id}")
async def disconnect_gmail(user_id: str):
    """Disconnect Gmail (Clean up both DB and Memory)."""
    
    # 1. Remove from Memory
    if user_id in active_monitors:
        del active_monitors[user_id]
    
    # 2. Remove from DB
    try:
        db.client.table("user_gmail_tokens").delete().eq("user_id", user_id).execute()
    except Exception as e:
        print(f"Error deleting from DB: {e}")

    # 3. Notify Client via Socket
    try:
        await socketio_service.emit_gmail_update(
            user_id,
            "disconnected",
            {"message": "Gmail monitoring stopped"}
        )
    except Exception as e:
        print(f"Socket emit failed: {e}")

    return {"message": "Gmail disconnected"}


@router.get("/debug/tokens/{user_id}")
async def debug_tokens(user_id: str):
    """Debug endpoint to check token status."""
    db_tokens = db.get_gmail_tokens(user_id)
    active_tokens = active_monitors.get(user_id)
    
    return {
        "user_id": user_id,
        "has_db_tokens": db_tokens is not None,
        "has_active_tokens": active_tokens is not None,
        "active_monitors_keys": list(active_monitors.keys()),
        "db_tokens_value": str(db_tokens) if db_tokens else None,
        "active_tokens_value": str(active_tokens) if active_tokens else None
    }


@router.get("/drafts/{user_id}")
async def list_drafts(user_id: str, limit: int = 10):
    """List Gmail drafts for a user, with parsed details."""
    # Try to get tokens from database first, then fall back to active_monitors
    tokens = db.get_gmail_tokens(user_id)
    
    if not tokens and user_id in active_monitors:
        tokens = active_monitors[user_id]
    
    if not tokens:
        raise HTTPException(
            status_code=400, 
            detail="Gmail not connected. Please connect your Gmail account first."
        )

    try:
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
                    "snippet": msg.get("snippet", ""),
                    "is_reply": "In-Reply-To" in headers or "References" in headers
                })
            except Exception as e:
                print(f"Failed to parse draft {d['id']}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch drafts: {str(e)}")
    
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
    print(f"DEBUG: Fetching inbox for user {user_id}")
    print(f"DEBUG: active_monitors keys: {list(active_monitors.keys())}")
    print(f"DEBUG: user_id in active_monitors: {user_id in active_monitors}")
    
    # Try to get tokens from database first, then fall back to active_monitors
    tokens = db.get_gmail_tokens(user_id)
    print(f"DEBUG: db.get_gmail_tokens returned: {tokens is not None}")
    
    if not tokens and user_id in active_monitors:
        tokens = active_monitors[user_id]
        print(f"DEBUG: Using tokens from active_monitors")
    
    if not tokens:
        print(f"DEBUG: No tokens found for user {user_id}")
        raise HTTPException(
            status_code=400, 
            detail="Gmail not connected. Please connect your Gmail account first."
        )
    
    try:
        print(f"DEBUG: Creating GmailService with tokens")
        gmail = GmailService(tokens)
        
        label_ids = ["INBOX"]
        if unread_only:
            label_ids.append("UNREAD")
        
        print(f"DEBUG: Fetching messages with query='{query}', labels={label_ids}, limit={limit}")
        messages = gmail.get_messages(query=query, label_ids=label_ids, max_results=limit)
        print(f"DEBUG: Got {len(messages)} messages")
        
        return {
            "count": len(messages),
            "messages": messages
        }
    except Exception as e:
        print(f"DEBUG: Exception in check_inbox: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch inbox: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch inbox: {str(e)}")


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


@router.delete("/draft/{user_id}/{draft_id}")
async def delete_draft(user_id: str, draft_id: str):
    """Delete a draft for the given user."""
    tokens = db.get_gmail_tokens(user_id)
    if not tokens and user_id in active_monitors:
        tokens = active_monitors[user_id]

    if not tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    gmail = GmailService(tokens)

    # Attempt to delete draft; treat 'not found' as success (idempotent)
    try:
        gmail.delete_draft(draft_id)
    except HttpError as he:
        status = None
        try:
            status = int(he.resp.status)
        except Exception:
            status = None

        # If draft is already gone, return success for idempotency
        if status in (404, 410):
            pass
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete draft: {he}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete draft: {e}")

    # After deletion, fetch updated drafts so we can emit them to clients
    parsed_drafts = []
    try:
        draft_refs = gmail.list_drafts(max_results=50)
        for d in draft_refs:
            try:
                draft = gmail.get_draft(d["id"])
                msg = draft["message"]
                headers = {h['name']: h['value'] for h in msg["payload"].get("headers", [])}
                body = gmail._get_body(msg["payload"])
                parsed_drafts.append({
                    "id": d["id"],
                    "subject": headers.get("Subject", ""),
                    "to": headers.get("To", ""),
                    "body": body,
                    "timestamp": msg.get("internalDate", ""),
                    "snippet": msg.get("snippet", ""),
                    "is_reply": "In-Reply-To" in headers or "References" in headers
                })
            except Exception:
                continue
    except Exception:
        parsed_drafts = []

    # Notify client via socket that drafts updated (include drafts for frontend convenience)
    try:
        await socketio_service.emit_gmail_update(
            user_id,
            "drafts_updated",
            {"message": "Draft deleted", "drafts": parsed_drafts}
        )
    except Exception:
        pass

    return {"success": True, "deleted": draft_id}


@router.post("/connect")
async def connect_gmail(
    request: GmailConnectRequest,
    background_tasks: BackgroundTasks
):
    user_id = request.user_id
    tokens = request.token
    
    print(f"DEBUG: Connecting user {user_id}")
    
    # 1. Fetch User Info from Google
    email_address = "unknown@gmail.com"
    full_name = "Marathon User"
    
    try:
        # Get Email
        gmail = GmailService(tokens)
        email_address = gmail.email_address
        
        # Get Name (Ignore avatar since column doesn't exist)
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {tokens.get('access_token')}"}
        ).json()
        
        full_name = user_info.get("name", email_address.split('@')[0])
        
    except Exception as e:
        print(f"Warning: Could not fetch Google user info: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch user info: {str(e)}")

    # 2. Create/Update Profile (NAME ONLY)
    try:
        print(f"DEBUG: ensuring profile exists for {user_id}")
        
        # We only save 'full_name' to avoid 'column not found' errors
        profile_data = {
            "full_name": full_name
            # "email": email_address  <-- Uncomment this if you added the email column
        }
        
        db.get_or_create_profile(user_id, profile_data)
        
        # Update if it existed but name was generic
        db.update_profile(user_id, profile_data)
        
    except Exception as e:
        print(f"ERROR: Database profile creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")

    # 3. Save Tokens to DATABASE (Primary Storage - Persistent)
    try:
        db.save_gmail_tokens(
            user_id=user_id,
            email=email_address,
            tokens={
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expiry": tokens.get("expiry"),
                "scopes": tokens.get("scopes", [])
            }
        )
        print(f"DEBUG: Saved tokens to DB for {user_id}")
    except Exception as e:
        print(f"ERROR: Could not save Gmail tokens to database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save Gmail tokens: {str(e)}")

    # 4. Cache in memory (Secondary - for quick access only)
    # This helps with performance but is not the source of truth
    active_monitors[user_id] = tokens
    print(f"DEBUG: Cached tokens in memory for {user_id}")

    # 5. Notify via Socket.IO
    await socketio_service.emit_gmail_update(
        user_id,
        "connected",
        {"message": "Gmail monitoring started"}
    )
    
    return {
        "success": True,
        "message": "Gmail connected successfully (stored in database)",
        "email": email_address,
        "user": full_name
    }