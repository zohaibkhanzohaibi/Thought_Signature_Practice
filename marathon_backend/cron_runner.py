#!/usr/bin/env python3
"""
Cron Runner Script for GitHub Actions

This script runs all active campaigns and checks emails for users.
Designed to be called by GitHub Actions on a schedule.

Usage:
    python -m marathon_backend.cron_runner [--api-url URL]
"""
import os
import sys
import time
import argparse
import subprocess
import requests
from typing import Optional

# Default to local server for GitHub Actions (starts its own server)
DEFAULT_API_URL = "http://localhost:8000"


def wait_for_server(api_url: str, max_wait: int = 30) -> bool:
    """Wait for server to be ready."""
    print(f"⏳ Waiting for server at {api_url}...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = requests.get(f"{api_url}/health", timeout=2)
            if r.status_code == 200:
                print("✅ Server is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    print("❌ Server did not become ready")
    return False


def get_active_campaigns(api_url: str) -> list:
    """Fetch all active campaigns from the database."""
    # Since we don't have a global campaigns list endpoint,
    # we'll query Supabase directly
    from supabase import create_client
    from dotenv import load_dotenv
    load_dotenv()
    
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    
    # Get all agent states (campaigns) that are active
    result = client.table("agent_states").select("id, user_id, config").execute()
    
    active = []
    for state in result.data or []:
        config = state.get("config", {})
        if not config.get("paused", False):
            active.append({
                "id": state["id"],
                "user_id": state["user_id"],
                "name": config.get("name", "Unnamed")
            })
    
    return active


def run_campaign(api_url: str, campaign_id: int) -> dict:
    """Trigger a campaign run."""
    try:
        r = requests.post(f"{api_url}/api/campaigns/{campaign_id}/run", timeout=120)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        else:
            return {"success": False, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_emails(api_url: str, user_id: str) -> dict:
    """Check emails for a user."""
    try:
        r = requests.post(f"{api_url}/api/gmail/{user_id}/check-emails", timeout=60)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        else:
            return {"success": False, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Run Marathon cron tasks")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--skip-server", action="store_true", help="Assume server is already running")
    args = parser.parse_args()
    
    server_process = None
    
    try:
        # Start server if needed
        if not args.skip_server:
            print("🚀 Starting FastAPI server...")
            server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "marathon_backend.main:app", 
                 "--host", "0.0.0.0", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if not wait_for_server(args.api_url):
                print("❌ Failed to start server")
                sys.exit(1)
        
        # Get active campaigns
        print("\n📋 Fetching active campaigns...")
        campaigns = get_active_campaigns(args.api_url)
        print(f"   Found {len(campaigns)} active campaigns")
        
        if not campaigns:
            print("ℹ️  No active campaigns to run")
            sys.exit(0)
        
        # Run each campaign
        results = {"success": 0, "failed": 0, "emails_checked": 0}
        processed_users = set()
        
        for campaign in campaigns:
            print(f"\n🔄 Running campaign {campaign['id']}: {campaign['name']}")
            result = run_campaign(args.api_url, campaign["id"])
            
            if result["success"]:
                print(f"   ✅ Success: {result.get('data', {}).get('message', 'OK')}")
                results["success"] += 1
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                results["failed"] += 1
            
            # Check emails for user (once per user)
            user_id = campaign["user_id"]
            if user_id not in processed_users:
                processed_users.add(user_id)
                print(f"   📧 Checking emails for user {user_id[:8]}...")
                email_result = check_emails(args.api_url, user_id)
                if email_result["success"]:
                    results["emails_checked"] += 1
        
        # Summary
        print("\n" + "="*50)
        print("📊 Cron Run Summary")
        print("="*50)
        print(f"   Campaigns successful: {results['success']}")
        print(f"   Campaigns failed:     {results['failed']}")
        print(f"   Users emails checked: {results['emails_checked']}")
        
        if results["failed"] > 0:
            sys.exit(1)
        
    finally:
        # Cleanup server
        if server_process:
            print("\n🛑 Shutting down server...")
            server_process.terminate()
            server_process.wait(timeout=5)


if __name__ == "__main__":
    main()
