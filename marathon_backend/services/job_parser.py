import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"

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
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Parsing error: {e}")
        # Fallback if AI fails
        return {
            "title": "Unknown Role",
            "company": "Unknown Company",
            "description": raw_text,
            "location": "Remote"
        }