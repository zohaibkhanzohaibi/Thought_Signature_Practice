# Marathon Agent - AI Job Search with Thought Signature Persistence

A sophisticated multi-session AI job search agent using Google's Gemini model with thought signature persistence and Supabase for state management.

## ✨ Features

- **Real Job Search** - Uses Google Search grounding to find actual job listings
- **Thought Signature Persistence** - Maintains AI reasoning continuity across sessions
- **Rate Limit Handling** - Automatic retry logic with graceful state saving
- **Smart Job Flow** - Applies to pending jobs first, then searches for new ones
- **Campaign Management** - Multi-day job search campaigns with daily limits
- **GitHub Actions** - Automated daily execution at 2 AM UTC

## 📁 Project Structure

```
thought_signature/
├── marathon_agent.py       # Unified agent with all commands
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (DO NOT COMMIT)
├── .gitignore              # Git ignore rules
└── .github/
    └── workflows/
        └── marathon_runner.yml  # Daily cron job
```

## 🚀 Quick Start

### 1. Setup Environment

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure .env

```env
SUPABASE_URL="your_supabase_url"
SUPABASE_KEY="your_supabase_service_key"
GEMINI_API_KEY="your_gemini_api_key"
```

### 3. Run Commands

```powershell
# Create a new job search campaign (interactive)
python marathon_agent.py --create

# Run one iteration for your campaign
python marathon_agent.py --run

# Check campaign status
python marathon_agent.py --status

# List all campaigns
python marathon_agent.py --list

# Run all active campaigns (for GitHub Actions/cron)
python marathon_agent.py --cron
```

## 📊 How It Works

### Job Flow
1. **Create Campaign** - Scout initial jobs and save them as "scouted"
2. **Daily Iteration** - First apply to pending scouted jobs, then search for new ones
3. **Deduplication** - Excludes previously applied jobs from new searches
4. **Campaign End** - Marks campaign inactive on final day

### Thought Signatures
When Gemini uses thinking mode, it generates a `thought_signature` - a cryptographic fingerprint of its reasoning. By persisting this:
- AI maintains context across sessions
- Reasoning chain continues seamlessly
- No repeated steps or lost context

### Rate Limit Handling
- Automatic retry (3 attempts, 60s wait)
- Detects daily quota vs per-minute limits
- Saves state before exit on quota exhaustion
- Resume seamlessly when quota resets

## 🔧 GitHub Actions Setup

### 1. Add Repository Secrets
Go to **Settings** → **Secrets and variables** → **Actions**:

| Secret | Value |
|--------|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `SUPABASE_URL` | Your Supabase URL |
| `SUPABASE_KEY` | Your Supabase service key |

### 2. Cron Schedule
Runs daily at 2 AM UTC. To change, edit `.github/workflows/marathon_runner.yml`:

```yaml
schedule:
  - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

## 🗄️ Database Schema

```sql
-- Profiles table
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT,
    contact_info JSONB,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent states (thought signatures + campaign config)
CREATE TABLE agent_states (
    user_id UUID PRIMARY KEY REFERENCES profiles(id),
    thought_signature TEXT,
    history JSONB DEFAULT '[]',
    internal_summary TEXT,
    thinking_level TEXT DEFAULT 'low',
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Job applications
CREATE TABLE job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    job_title TEXT,
    company_name TEXT,
    source_url TEXT,
    status TEXT DEFAULT 'scouted',  -- scouted, applied, interview, offer
    replies_log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 📝 License

MIT License
