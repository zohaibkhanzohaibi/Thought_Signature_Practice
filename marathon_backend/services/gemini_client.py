import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Set up Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment or .env file")


genai.configure(api_key=GEMINI_API_KEY)

# Use Gemma 3B Instruct (or update to 12B if available)
MODEL =  "gemini-3-flash-preview" # "gemini-2.5-flash"

def call_gemini(prompt: str, system: str = None, max_tokens: int = 2048, temperature: float = 0.3) -> str:
    """
    Call Gemini Pro API with a prompt and optional system message.
    """
    model = genai.GenerativeModel(MODEL)
    if system:
        full_prompt = f"{system}\n\n{prompt}"
    else:
        full_prompt = prompt
    response = model.generate_content(full_prompt, generation_config={
        "temperature": temperature,
        "max_output_tokens": max_tokens
    })
    return response.text.strip() if hasattr(response, "text") else str(response)
