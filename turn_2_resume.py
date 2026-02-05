"""
turn_2_resume.py - Marathon Agent: Resume Session

This script "wakes up," loads the thought signature from Supabase, 
and continues the task with full context preservation.
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


def resume_marathon():
    """Resume a marathon agent session from saved state."""
    
    # 1. Fetch State from Supabase
    res = supabase.table("agent_states").select("*").eq("user_id", "test_user_001").single().execute()
    
    if not res.data:
        print("❌ No saved state found for this user. Run turn_1_plan.py first.")
        return
    
    state = res.data
    
    # 2. Rehydrate History (Crucial: Include the Signature in the previous model turn)
    history = state['history']
    
    print(f"📜 Loaded {len(history)} messages from history")
    print(f"🔐 Previous signature: {state['last_signature'][:50] if state.get('last_signature') else 'None'}...")
    
    # 3. Ask for Step 2
    new_prompt = "Great, let's proceed with Step 2 of the plan."
    
    # Convert history to proper format for chat
    formatted_history = []
    for msg in history:
        content_parts = []
        for part in msg.get('parts', []):
            if 'text' in part:
                # Include thought_signature if present
                if part.get('thought_signature'):
                    content_parts.append(types.Part(
                        text=part['text'],
                        thought_signature=part['thought_signature']
                    ))
                else:
                    content_parts.append(types.Part(text=part['text']))
        
        formatted_history.append(types.Content(
            role=msg['role'],
            parts=content_parts
        ))
    
    # Use chat mode to maintain the rehydrated history
    chat = client.chats.create(
        model=MODEL_ID, 
        history=formatted_history,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )
    
    response = chat.send_message(new_prompt)

    print("\n--- REHYDRATED RESPONSE ---")
    print(response.text)
    
    # 4. Extract the NEW signature for the next turn
    new_signature = None
    if response.candidates and response.candidates[0].content.parts:
        last_part = response.candidates[0].content.parts[-1]
        if hasattr(last_part, 'thought_signature') and last_part.thought_signature:
            new_signature = last_part.thought_signature
    
    # 5. Update history with new messages
    history.append({"role": "user", "parts": [{"text": new_prompt}]})
    history.append({"role": "model", "parts": [{"text": response.text, "thought_signature": new_signature}]})
    
    # 6. Save updated state to Supabase
    supabase.table("agent_states").update({
        "last_signature": new_signature,
        "history": history
    }).eq("user_id", "test_user_001").execute()
    
    print("\n✅ State updated in Supabase.")


if __name__ == "__main__":
    resume_marathon()
