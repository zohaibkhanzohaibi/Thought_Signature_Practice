import os
import json
from dotenv import load_dotenv
from .gemini_client import call_gemini

load_dotenv()

async def parse_job_text(raw_text: str) -> dict:
    prompt = f"""
    Analyze the following job post text (which might be a LinkedIn post, email, or raw description).
    Extract the following fields into a pure JSON object:
    - title (Job role)
    - company (Company name)
    - location (City, Country or Remote)
    - contact_email (Look for email addresses in the text, return null if none)
    - source_url (If a link exists in text, return it, else null)
    - summary (A clean version of the description, removing "Show more" or UI artifacts)

    RAW TEXT:
    {raw_text[:5000]}
    """

    try:
        # Use OpenRouter-backed wrapper to generate structured JSON
        response_text = call_gemini(prompt, temperature=0.2)
        return json.loads(response_text)
    except Exception as e:
        print(f"Parsing error: {e}")
        # Fallback if AI fails
        return {
            "title": "Unknown Role",
            "company": "Unknown Company",
            "description": raw_text,
            "location": "Remote"
        }