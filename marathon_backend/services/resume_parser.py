"""
Resume Parser Service - Extracts text from PDF resumes.
"""
import os
from typing import Optional, Dict
from pypdf import PdfReader


def parse_pdf(file_path: str) -> Optional[str]:
    """
    Extract text content from a PDF resume.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or None if failed
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    print(f"📄 Parsing resume: {file_path}")
    
    try:
        reader = PdfReader(file_path)
        full_text = []
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        
        combined = "\n".join(full_text).strip()
        print(f"✅ Extracted {len(combined)} characters")
        return combined
        
    except Exception as e:
        print(f"❌ PDF parsing error: {e}")
        return None


def parse_pdf_to_structured(file_path: str) -> Optional[Dict]:
    """
    Parse PDF and attempt to extract structured information.
    Uses AI to structure the raw text.
    """
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import json
    
    load_dotenv()
    
    raw_text = parse_pdf(file_path)
    if not raw_text:
        return None
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""Parse this resume text and extract structured information.

--- RESUME TEXT ---
{raw_text}

Return JSON with this structure:
{{
    "personal_info": {{
        "name": "Full Name",
        "email": "email@example.com",
        "phone": "+1234567890",
        "linkedin_url": "https://linkedin.com/in/...",
        "github_url": "https://github.com/..."
    }},
    "summary": "Professional summary if present",
    "education": [
        {{"school": "...", "degree": "...", "dates": "...", "location": "..."}}
    ],
    "experience": [
        {{"company": "...", "role": "...", "dates": "...", "location": "...", "bullets": ["..."]}}
    ],
    "projects": [
        {{"name": "...", "tech_stack": "...", "bullets": ["..."]}}
    ],
    "skills": ["Python", "JavaScript", "SQL"],
    "certifications": ["..."]
}}

Extract all available information. Use null for missing fields.
Return ONLY valid JSON.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"❌ Structured parsing failed: {e}")
        # Return basic structure with raw text
        return {
            "raw_text": raw_text,
            "personal_info": {},
            "education": [],
            "experience": [],
            "projects": [],
            "skills": []
        }


async def parse_resume_bytes(content: bytes, filename: str) -> Optional[Dict]:
    """
    Parse resume from uploaded bytes (for API use).
    """
    import tempfile
    import os
    
    # Save to temp file
    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = parse_pdf_to_structured(tmp_path)
        return result
    finally:
        os.unlink(tmp_path)
