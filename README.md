# Marathon Agent - Thought Signature Persistence

A sophisticated AI agent that maintains reasoning continuity across sessions using Google's Gemini model and Supabase for state persistence.

## 📁 Project Structure

```
thought_signature/
├── .env                    # Environment variables (DO NOT COMMIT)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
├── turn_1_plan.py          # Script 1: Start marathon & save signature
├── turn_2_resume.py        # Script 2: Resume marathon with signature
├── universal_marathon_runner.py  # Multi-user campaign processor
└── .github/
    └── workflows/
        └── marathon_runner.yml  # GitHub Actions workflow
```

## 🚀 Quick Start

### 1. Setup Virtual Environment

```powershell
# Already created in venv/ folder
.\venv\Scripts\Activate.ps1
```

### 2. Configure Environment Variables

Edit `.env` file and add your Gemini API key:

```env
SUPABASE_URL="https://dmmdmuemwkcbbqqvpxpp.supabase.co"
SUPABASE_KEY="your_supabase_key"
GEMINI_API_KEY="your_gemini_api_key_here"  # <-- Add this!
```

### 3. Setup Supabase Table

Run this SQL in your Supabase SQL Editor:

```sql
-- Create the agent_states table
CREATE TABLE IF NOT EXISTS agent_states (
    user_id TEXT PRIMARY KEY,
    last_signature TEXT,
    history JSONB DEFAULT '[]'::jsonb,
    campaign_config JSONB DEFAULT '{}'::jsonb,
    internal_summary TEXT,
    thinking_level TEXT DEFAULT 'low',
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY;
```

### 4. Run the Scripts

```powershell
# Start a marathon (creates initial plan)
python turn_1_plan.py

# Resume the marathon (continues from saved state)
python turn_2_resume.py

# Run all user campaigns (used by GitHub Actions)
python universal_marathon_runner.py

# Create demo missions for testing
python universal_marathon_runner.py --demo
```

## 🔧 GitHub Actions Setup

### Step 1: Push to GitHub

```powershell
git init
git add .
git commit -m "Initial commit: Marathon Agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/thought_signature.git
git push -u origin main
```

### Step 2: Add Repository Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `SUPABASE_URL` | `https://dmmdmuemwkcbbqqvpxpp.supabase.co` |
| `SUPABASE_KEY` | Your Supabase service role key |

### Step 3: Enable GitHub Actions

The workflow is already configured in `.github/workflows/marathon_runner.yml`

It will:
- Run automatically every 6 hours
- Process all active user campaigns
- Can be triggered manually from the Actions tab

### Step 4: Manually Trigger (Optional)

1. Go to **Actions** tab in your repository
2. Select **"Marathon Agent Runner"** workflow
3. Click **"Run workflow"**

## 📊 How It Works

### The "DNA" of Reasoning: Thought Signatures

When Gemini uses "thinking mode," it generates a `thought_signature` - a cryptographic fingerprint of its reasoning chain. By persisting this signature:

1. **Turn 1**: Agent creates a plan, we save the signature
2. **Turn 2+**: Agent loads the signature, reasoning continues seamlessly

Without the signature, the model "forgets" its previous reasoning and may repeat steps.

### Campaign Configuration

Users can have custom job-hunting campaigns:

```json
{
  "target_role": "Python Developer",
  "daily_limit": 10,
  "total_days": 4,
  "start_date": "2026-02-05",
  "current_day": 1,
  "jobs_applied_today": 0,
  "is_active": true
}
```

The `universal_marathon_runner.py` reads these configs and processes each user independently.

## 🔒 Security Notes

- **NEVER commit `.env`** - it's in `.gitignore`
- Use GitHub Secrets for CI/CD
- The Supabase key uses `service_role` - keep it private
- For production, implement proper Row Level Security (RLS)

## 🛠️ Customization

### Change Cron Schedule

Edit `.github/workflows/marathon_runner.yml`:

```yaml
on:
  schedule:
    # Current: Every 6 hours
    - cron: '0 */6 * * *'
    
    # Examples:
    # Every hour:       '0 * * * *'
    # Every 12 hours:   '0 */12 * * *'
    # Daily at 9 AM:    '0 9 * * *'
    # Every Monday:     '0 0 * * 1'
```

### Add Job Scraping

Replace the `scout_jobs()` function in `universal_marathon_runner.py` with actual API calls:

```python
def scout_jobs(query: str, location: str = "Remote"):
    # Example: LinkedIn API, Indeed API, etc.
    import requests
    response = requests.get(f"https://api.example.com/jobs?q={query}&location={location}")
    return response.json()['jobs']
```

## 📝 License

MIT License - Use freely for your hackathon and beyond!
