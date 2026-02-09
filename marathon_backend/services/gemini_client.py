import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

# Set up OpenRouter API key from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    # Fallback to checking GEMINI_API_KEY if OPENROUTER is missing, 
    # but strictly we should use OPENROUTER_KEY for OpenRouter.
    # For now, let's assume the user set OPENROUTER_API_KEY as requested.
    print("⚠️ OPENROUTER_API_KEY not found. Checking GEMINI_API_KEY as backup...")
    OPENROUTER_API_KEY = os.getenv("GEMINI_API_KEY")
    
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in environment or .env file")

# Use Google Gemini 2.0 Flash via OpenRouter
MODEL = "google/gemini-2.0-flash-001"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_gemini(prompt: str, system: str = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
    """
    Call OpenRouter API (proxying Gemini) with a prompt and optional system message.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/zohaibkhanzohaibi/Thought_Signature_Practice", # Verified Requirement
        "X-Title": "Marathon Job Search", # Verified Requirement
        "Content-Type": "application/json"
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "repetition_penalty": 1.0
    }

    try:
        # standard timeout of 60s
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            # OpenRouter/OpenAI format: choices[0].message.content
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"].get("content", "")
                return content.strip()
            else:
                return f"Error: No content in response. Raw: {str(data)}"
                
    except httpx.HTTPStatusError as e:
        return f"API Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Request Failed: {str(e)}"
