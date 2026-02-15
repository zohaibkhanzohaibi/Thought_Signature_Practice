import os
import json
import inspect
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

    Return ONLY a valid JSON object. Do not include markdown formatting like ```json.

    RAW TEXT:
    {raw_text[:5000]}
    """

    try:
        # Call the AI model
        response_text = call_gemini(prompt, temperature=0.2)
        
        # Safety net: If call_gemini is an async function, await it
        if inspect.iscoroutine(response_text):
            response_text = await response_text

        # Catch empty responses
        if not response_text:
            raise ValueError("AI returned an empty string.")

        # Log the raw text to your terminal so you can see what is breaking
        print(f"🤖 RAW AI RESPONSE:\n{response_text}\n{'-'*40}")

        # Clean up Markdown backticks if the AI ignored the instruction
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()

        return json.loads(text)
        
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        # Fallback if AI fails
        return {
            "title": "Unknown Role",
            "company": "Unknown Company",
            "description": raw_text,
            "location": "Remote"
        }