import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

# Use Google Gemini 2.0 Flash via OpenRouter or Google GenAI
# Default preference: Google GenAI (for native Grounding) > OpenRouter
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not GEMINI_API_KEY and not OPENROUTER_API_KEY:
    raise RuntimeError("Neither GEMINI_API_KEY nor OPENROUTER_API_KEY set in environment")

# Configure Google GenAI if key is present
if GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)


def call_gemini(prompt: str, system: str = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
    """
    Call Gemini API with a prompt and optional system message.
    Prefers Google GenAI SDK for native Grounding support, falls back to OpenRouter.
    """
    
    # --- 1. Try Google GenAI SDK (with Grounding) ---
    if GEMINI_API_KEY:
        try:
            # Use a model that supports grounding
            # Note: 2.0 Flash is 'gemini-2.0-flash' or 'gemini-2.0-flash-exp'
            # We use 'gemini-2.0-flash' as stable endpoint, or 'gemini-1.5-flash' if needed.
            # Let's try gemini-2.0-flash.
            model_name = "gemini-2.0-flash" 
            
            # Configure tools for Grounding if prompt implies search
            # We use 'google_search_retrieval' which matches the API proto definition for the Python SDK
            tools = [{"google_search_retrieval": {}}]
            
            model = genai.GenerativeModel(model_name=model_name, system_instruction=system, tools=tools)
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "Error: Empty response from Gemini."
                
        except Exception as e:
            print(f"⚠️ Google GenAI SDK failed: {e}. Falling back to OpenRouter/HTTP...")
            # Fallthrough to OpenRouter if configured


    # --- 2. Fallback to OpenRouter (No explicit Grounding tool yet) ---
    if OPENROUTER_API_KEY:
        OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
        MODEL = "google/gemini-2.0-flash-001"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/zohaibkhanzohaibi/Thought_Signature_Practice",
            "X-Title": "Marathon Job Search",
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
            "max_tokens": max_tokens
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(OPENROUTER_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"].get("content", "").strip()
                else:
                    return f"Error: No content. Raw: {str(data)}"
        except Exception as e:
            return f"OpenRouter Request Failed: {str(e)}"
    
    return "Error: No valid API configuration found."
