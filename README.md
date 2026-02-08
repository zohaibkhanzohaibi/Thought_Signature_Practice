# Marathon Agent - AI Job Search Backend

A FastAPI backend for automated job searching, resume tailoring, and Gmail integration using Google Gemini AI with thought signature persistence.

## ✨ Features

- **AI Job Search** - Uses Gemini with Google Search grounding to find real job listings
- **Resume Tailoring** - Multi-agent pipeline (Recruiter → Writer → Critic) for ATS-optimized resumes
- **LaTeX PDF Generation** - Professional resume PDFs with Jinja2 templating
- **Gmail Integration** - Per-user OAuth2, draft creation, and email reply agent
- **Thought Signature Persistence** - Maintains AI reasoning continuity across sessions
- **GitHub Portfolio Sync** - Fetches repos and tech stack for resume enhancement

## 📁 Project Structure

```
thought_signature/
├── marathon_backend/           # FastAPI application
│   ├── main.py                 # App entry point
│   ├── models/
│   │   ├── database.py         # Supabase client & queries
│   │   └── schemas.py          # Pydantic models
│   ├── routers/
│   │   ├── profile.py          # User profile endpoints
│   │   ├── campaigns.py        # Job search campaigns
│   │   ├── jobs.py             # Job applications & tailoring
│   │   └── gmail.py            # Gmail OAuth & drafts
│   ├── services/
│   │   ├── job_search.py       # AI job search with Google grounding
│   │   ├── resume_tailor.py    # Multi-agent resume tailoring
│   │   ├── resume_parser.py    # PDF resume parsing
│   │   ├── pdf_renderer.py     # LaTeX resume generation
│   │   ├── github_service.py   # GitHub portfolio fetching
│   │   ├── gmail_service.py    # Gmail API operations
│   │   └── email_reply_agent.py # Automated email monitoring
│   ├── templates/
│   │   └── resume.tex          # ATS-optimized LaTeX template
│   └── cron_runner.py          # GitHub Actions cron script
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx             # Main app component
│   │   ├── api.ts              # API client
│   │   └── components/         # UI components
│   ├── package.json
│   └── vite.config.ts
├── migrations/
│   └── 001_enhanced_schema.sql # Database schema
├── .github/
│   └── workflows/
│       └── marathon_runner.yml # Daily cron workflow
├── resumes/                    # Generated PDF storage
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

## 🚀 Quick Start

### 1. Setup Backend

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Setup Frontend

```powershell
cd frontend
npm install
```

### 3. Configure .env

```env
# Required
SUPABASE_URL="your_supabase_url"
SUPABASE_KEY="your_supabase_service_key"
GEMINI_API_KEY="your_gemini_api_key"

# Gmail OAuth (optional)
GOOGLE_CLIENT_ID="your_client_id"
GOOGLE_CLIENT_SECRET="your_client_secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/gmail/callback"

# GitHub (optional, increases rate limit)
GITHUB_TOKEN="your_github_pat"
```

### 4. Run Database Migration

Apply the schema to your Supabase project:
```sql
-- Run migrations/001_enhanced_schema.sql in Supabase SQL Editor
```

### 5. Start the Servers

```powershell
# Terminal 1: Start backend (port 8000)
uvicorn marathon_backend.main:app --reload --port 8000

# Terminal 2: Start frontend (port 3000)
cd frontend
npm run dev
```

### 6. Access the App

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile/{user_id}` | Get user profile |
| POST | `/api/profile/{user_id}/resume/upload` | Upload & parse resume PDF |
| POST | `/api/profile/{user_id}/github/sync` | Sync GitHub portfolio |

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/campaigns/` | Create job search campaign |
| GET | `/api/campaigns/user/{user_id}` | List user campaigns |
| POST | `/api/campaigns/{id}/run` | Execute campaign search |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs/user/{user_id}` | List job applications |
| POST | `/api/jobs/{id}/tailor` | Tailor resume for job |
| POST | `/api/jobs/{id}/generate-pdf` | Generate resume PDF |
| POST | `/api/jobs/{id}/create-draft` | Create Gmail draft |

### Gmail
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gmail/auth` | Start OAuth flow |
| GET | `/api/gmail/callback` | OAuth callback |
| POST | `/api/gmail/{user_id}/check-emails` | Check for new emails |

## 🔧 LaTeX Setup (Optional)

For PDF generation, install a LaTeX distribution:

**Windows:**
```powershell
# Using Chocolatey
choco install miktex

# Or download from https://miktex.org/download
```

**Alternative:** The system falls back to Tectonic if pdflatex is unavailable.

## 🗄️ Database Schema

Key tables in Supabase:
- `user_profiles` - User info, parsed resume, portfolio
- `agent_states` - Campaign configs with thought signatures
- `job_applications` - Jobs with tailored resumes & status
- `campaign_runs` - Execution logs
- `user_gmail_tokens` - Per-user OAuth tokens (encrypted)
- `email_threads` - Tracked email conversations

## 🔐 Security Notes

- Gmail tokens stored encrypted in database
- Per-user OAuth isolation
- Service key should have RLS policies enabled
- Never commit `.env` file

## ⏰ GitHub Actions (Automated Cron)

The workflow runs daily at 2 AM UTC to:
1. Start the FastAPI server temporarily
2. Run all active campaigns (job search)
3. Check emails for each user
4. Shut down

### Required Secrets

Go to **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `GH_PAT` | GitHub personal access token (optional) |
| `GOOGLE_CLIENT_ID` | Gmail OAuth client ID (optional) |
| `GOOGLE_CLIENT_SECRET` | Gmail OAuth secret (optional) |

### Manual Trigger

Run manually from **Actions → Marathon Agent Runner → Run workflow**.

## 📄 License

MIT
