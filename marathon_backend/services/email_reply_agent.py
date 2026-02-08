"""
Email Reply Agent - LangGraph-based email monitoring and reply generation.
Converted from Ahmed's openrouter_email_agent.py to use Gemini.

Features:
- Monitors inbox for job-related emails
- Classifies emails (job response vs. other)
- Generates polite replies
- Creates drafts instead of sending directly
- Labels processed emails
"""
import os
import time
from typing import Dict, List, Optional
from typing_extensions import TypedDict
from datetime import datetime

from google import genai
from google.genai import types
from dotenv import load_dotenv

from .gmail_service import GmailService

load_dotenv()

# Gemini Configuration
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"


class EmailAgentState(TypedDict):
    """State for the email processing workflow."""
    initialized: bool
    processed_email_ids: List[str]
    new_email: Optional[Dict]
    email_classification: str
    llm_output: str
    user_id: str


def call_gemini(prompt: str, system_prompt: str = None, temperature: float = 0.3) -> str:
    """Call Gemini API with retry logic."""
    from .job_search import call_with_retry
    
    contents = prompt
    if system_prompt:
        contents = [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    
    response = call_with_retry(lambda: client.models.generate_content(
        model=MODEL_ID,
        contents=contents,
        config=types.GenerateContentConfig(temperature=temperature)
    ))
    return response.text.strip()


class EmailReplyAgent:
    """
    LangGraph-style email agent using Gemini.
    Monitors inbox, classifies emails, generates replies.
    """
    
    def __init__(self, user_id: str, gmail_tokens: Dict):
        """
        Initialize the email reply agent.
        
        Args:
            user_id: User ID for database operations
            gmail_tokens: OAuth tokens for Gmail
        """
        self.user_id = user_id
        self.gmail = GmailService(gmail_tokens)
        self.state: EmailAgentState = {
            "initialized": False,
            "processed_email_ids": [],
            "new_email": None,
            "email_classification": "",
            "llm_output": "",
            "user_id": user_id
        }
    
    def check_for_new_emails(self) -> EmailAgentState:
        """Check inbox for new unprocessed emails."""
        print("📬 Checking for new emails...")
        
        if not self.state["initialized"]:
            print("   Initializing state for the first time...")
            self.state["initialized"] = True
            
            # Get recent emails and mark as processed (initial load)
            messages = self.gmail.get_messages(
                query="",
                label_ids=["INBOX"],
                max_results=10
            )
            self.state["processed_email_ids"] = [msg["id"] for msg in messages]
            self.state["new_email"] = None
            print(f"   Initial emails marked as processed: {len(self.state['processed_email_ids'])}")
            return self.state
        
        # Check for new emails
        messages = self.gmail.get_messages(
            query="is:unread",
            label_ids=["INBOX"],
            max_results=10
        )
        
        processed_ids = set(self.state["processed_email_ids"])
        new_emails = [msg for msg in messages if msg["id"] not in processed_ids]
        
        if new_emails:
            self.state["new_email"] = new_emails[0]
            print(f"   📨 New email from: {new_emails[0].get('from', 'Unknown')}")
        else:
            self.state["new_email"] = None
            print("   No new emails")
        
        return self.state
    
    def classify_email(self) -> EmailAgentState:
        """Classify email as job-related or not."""
        email = self.state.get("new_email")
        
        if not email:
            self.state["email_classification"] = "No new email"
            return self.state
        
        email_content = f"""From: {email.get('from', '')}
Subject: {email.get('subject', '')}

{email.get('body', email.get('snippet', ''))}"""

        system_prompt = """Analyze the following email and determine if it is a direct response to a job application.

Criteria for "Yes":
- It mentions a specific job title I applied for
- It mentions reviewing my resume or application
- It is an invitation for an interview, technical test, or rejection
- It is a human or automated update regarding my status in a hiring pipeline

Criteria for "No":
- It is a marketing email, newsletter, or discount offer
- It is a generic "Job Alert" for new roles I haven't applied to
- It is spam, social media notifications, or personal mail unrelated to jobs

Instruction: Respond with ONLY the word "Yes" or "No". Do not provide any explanation."""

        result = call_gemini(
            prompt=f"Email content:\n\n{email_content}",
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        classification = result.lower().strip()
        if "yes" in classification:
            self.state["email_classification"] = "Yes"
        elif "no" in classification:
            self.state["email_classification"] = "No"
        else:
            self.state["email_classification"] = "No"
        
        print(f"   📊 Email classified as: {self.state['email_classification']}")
        return self.state
    
    def generate_response(self) -> EmailAgentState:
        """Generate a polite reply to job-related email."""
        email = self.state.get("new_email")
        
        if not email:
            return self.state
        
        email_content = f"""From: {email.get('from', '')}
Subject: {email.get('subject', '')}

{email.get('body', email.get('snippet', ''))}"""

        system_prompt = """You are an assistant that generates email replies. 
Respond politely in English. Write the email as if you were the job applicant.
Like 'Dear Mr. x, thanks for your email...'. 
Only provide the email text, no intro like 'Here is the polite reply:' or any other introduction!

Keep it professional and concise. Express enthusiasm for the opportunity if relevant."""

        response = call_gemini(
            prompt=f"Email content:\n\n{email_content}\n\nWrite a polite reply.",
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        self.state["llm_output"] = response
        print(f"   ✍️ Generated response ({len(response)} chars)")
        return self.state
    
    def create_draft_response(self) -> EmailAgentState:
        """Create a Gmail draft with the generated response."""
        email = self.state.get("new_email")
        
        if not email:
            print("   No email to create draft for")
            return self.state
        
        sender = email.get("from", "")
        subject = email.get("subject", "No Subject")
        message_id = email.get("message_id")
        response_text = self.state.get("llm_output", "")
        
        if not response_text:
            print("   No response generated")
            return self.state
        
        # Create draft
        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
        
        draft_id = self.gmail.create_draft(
            to=sender,
            subject=reply_subject,
            body=response_text,
            in_reply_to=message_id
        )
        
        print(f"   📝 Draft created: {draft_id}")
        return self.state
    
    def flag_email(self) -> EmailAgentState:
        """Flag email based on classification and mark as processed."""
        email = self.state.get("new_email")
        
        if not email:
            print("   No email to flag")
            return self.state
        
        email_id = email["id"]
        classification = self.state.get("email_classification", "").lower()
        
        # Add label based on classification
        if classification == "yes":
            label_name = "MarathonAgent/JobResponse"
        else:
            label_name = "MarathonAgent/Other"
        
        try:
            self.gmail.add_label(email_id, label_name)
            self.gmail.mark_as_read(email_id)
            print(f"   🏷️ Labeled as: {label_name}")
        except Exception as e:
            print(f"   ⚠️ Could not label email: {e}")
        
        # Mark as processed
        self.state["new_email"] = None
        if email_id not in self.state["processed_email_ids"]:
            self.state["processed_email_ids"].append(email_id)
        
        return self.state
    
    def run_once(self) -> Dict:
        """
        Run one iteration of the email processing workflow.
        
        Returns workflow:
            check_emails → classify_email → 
                if job-related: generate_response → create_draft → flag_email
                else: flag_email
        """
        # Step 1: Check for new emails
        self.check_for_new_emails()
        
        if not self.state.get("new_email"):
            return {
                "status": "no_new_emails",
                "processed_count": len(self.state["processed_email_ids"])
            }
        
        # Step 2: Classify the email
        self.classify_email()
        
        classification = self.state.get("email_classification", "").lower()
        
        # Step 3: Process based on classification
        if classification == "yes":
            # Job-related: generate response and create draft
            self.generate_response()
            self.create_draft_response()
        
        # Step 4: Flag and mark as processed
        self.flag_email()
        
        return {
            "status": "processed",
            "classification": classification,
            "email_subject": self.state.get("new_email", {}).get("subject", ""),
            "draft_created": classification == "yes",
            "processed_count": len(self.state["processed_email_ids"])
        }
    
    def run_continuous(self, interval_seconds: int = 30, max_iterations: int = None):
        """
        Run email checker continuously.
        
        Args:
            interval_seconds: Seconds between checks
            max_iterations: Maximum iterations (None for infinite)
        """
        print(f"🚀 Starting email reply agent (checking every {interval_seconds}s)...")
        
        iteration = 0
        first_run = True
        
        while max_iterations is None or iteration < max_iterations:
            try:
                result = self.run_once()
                print(f"   Iteration {iteration + 1}: {result['status']}")
                
                iteration += 1
                
                # Shorter wait on first run, then normal interval
                wait_time = 2 if first_run else interval_seconds
                first_run = False
                
                if max_iterations is None or iteration < max_iterations:
                    time.sleep(wait_time)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Email agent stopped by user")
                break
            except Exception as e:
                print(f"   ❌ Error: {e}")
                time.sleep(interval_seconds)
        
        print(f"✅ Email agent finished. Processed {len(self.state['processed_email_ids'])} emails.")


async def process_single_email(
    user_id: str,
    gmail_tokens: Dict,
    email: Dict
) -> Dict:
    """
    Process a single email (classify + optionally generate reply).
    Useful for API endpoints.
    
    Args:
        user_id: User ID
        gmail_tokens: Gmail OAuth tokens
        email: Email dict from get_messages()
        
    Returns:
        Dict with classification and optional draft_id
    """
    agent = EmailReplyAgent(user_id, gmail_tokens)
    agent.state["initialized"] = True
    agent.state["new_email"] = email
    
    # Classify
    agent.classify_email()
    classification = agent.state.get("email_classification", "")
    
    result = {
        "email_id": email.get("id"),
        "subject": email.get("subject"),
        "classification": classification,
        "draft_created": False
    }
    
    # Generate reply if job-related
    if classification.lower() == "yes":
        agent.generate_response()
        agent.create_draft_response()
        result["draft_created"] = True
        result["reply_preview"] = agent.state.get("llm_output", "")[:200] + "..."
    
    return result
