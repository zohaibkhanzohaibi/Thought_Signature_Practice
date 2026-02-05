"""
turn_1_plan.py - Marathon Agent: Initial Plan Creation

This script starts the conversation, extracts the thought signature, and saves it to Supabase.
The thought_signature is the "DNA" of the agent's reasoning chain.
"""

import os
from google import genai
from google.genai import types
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Setup Clients
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

MODEL_ID = "gemini-2.0-flash-thinking-exp"  # Use appropriate model with thinking support


def start_marathon():
    """Initialize a marathon agent session with a planning prompt."""
    
    user_prompt = "I want to find a SQL job in Karachi. Create a 3-step plan."
    
    # 1. Call Gemini with thinking enabled for planning
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )

    # 2. Extract Text and Signature
    # In Gemini, signatures are attached to the Content Part
    model_text = response.text
    
    # Extract thought_signature from the last part
    signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            signature = last_part.thought_signature

    print(f"Gemini's Plan:\n{model_text}")
    
    if signature:
        print(f"\nCaptured Signature: {signature[:50]}...")
    else:
        print("\nNo thought signature captured (model may not support it)")

    # 3. Save to Supabase (State Persistence)
    # First, get or create a profile for the test user
    profile_res = supabase.table("profiles").select("id").eq("full_name", "Test User").execute()
    
    if profile_res.data:
        user_id = profile_res.data[0]['id']
    else:
        # Create a new profile
        new_profile = supabase.table("profiles").insert({
            "full_name": "Test User",
            "contact_info": {"email": "test@example.com"},
            "summary": "Test user for marathon agent"
        }).execute()
        user_id = new_profile.data[0]['id']
    
    state_data = {
        "user_id": user_id,
        "thought_signature": signature,
        "internal_summary": f"Plan created: {model_text[:100]}...",
        "thinking_level": "low",
        "history": [
            {"role": "user", "parts": [{"text": user_prompt}]},
            {"role": "model", "parts": [{"text": model_text, "thought_signature": signature}]}
        ]
    }
    
    # Upsert based on user_id
    result = supabase.table("agent_states").upsert(state_data, on_conflict="user_id").execute()
    print("\n✅ State saved to Supabase. Script exiting...")
    
    return result


if __name__ == "__main__":
    start_marathon()
