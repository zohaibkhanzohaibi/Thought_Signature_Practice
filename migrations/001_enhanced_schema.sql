-- Migration 001: Enhanced Schema for Job Application Backend
-- Run this in Supabase SQL Editor

-- ============================================
-- 1. ENHANCE PROFILES TABLE
-- ============================================

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS github_username TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS master_resume_url TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS parsed_resume JSONB DEFAULT '{}'::jsonb;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS portfolio_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS skills TEXT[] DEFAULT '{}';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS experience_years INTEGER DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS preferred_locations TEXT[] DEFAULT '{}';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS target_roles TEXT[] DEFAULT '{}';

-- ============================================
-- 2. ENHANCE JOB_APPLICATIONS TABLE
-- ============================================

-- Add new columns for full pipeline tracking
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS job_description TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS jd_analysis JSONB DEFAULT '{}'::jsonb;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS tailored_resume JSONB DEFAULT '{}'::jsonb;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS cover_email TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS resume_pdf_path TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS gmail_draft_id TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS gmail_thread_id TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS gmail_message_id TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS company_email TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS posted_date TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS match_score INTEGER DEFAULT 0;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS salary_range TEXT;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;
ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ DEFAULT NOW();

-- Update status constraint to include full lifecycle
ALTER TABLE job_applications DROP CONSTRAINT IF EXISTS job_applications_status_check;
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'job_applications_status_check'
    ) THEN
        ALTER TABLE job_applications ADD CONSTRAINT job_applications_status_check 
            CHECK (status IN ('scouted', 'analyzing', 'tailored', 'drafted', 'sent', 'replied', 'interview', 'offer', 'rejected', 'withdrawn'));
    END IF;
END $$;

-- ============================================
-- 3. CREATE USER_GMAIL_TOKENS TABLE (Per-User OAuth)
-- ============================================

CREATE TABLE IF NOT EXISTS user_gmail_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    email_address TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMPTZ,
    scopes TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ============================================
-- 4. CREATE EMAIL_THREADS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS email_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    job_application_id UUID REFERENCES job_applications(id) ON DELETE SET NULL,
    gmail_thread_id TEXT NOT NULL,
    gmail_message_id TEXT,
    subject TEXT,
    last_sender TEXT,
    last_snippet TEXT,
    message_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'needs_reply', 'replied', 'waiting', 'closed')),
    is_job_related BOOLEAN DEFAULT false,
    auto_reply_draft_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(gmail_thread_id, user_id)
);

-- ============================================
-- 5. CREATE CAMPAIGN_RUNS TABLE (Track Each Cron Run)
-- ============================================

CREATE TABLE IF NOT EXISTS campaign_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    campaign_day INTEGER NOT NULL,
    jobs_scouted INTEGER DEFAULT 0,
    jobs_tailored INTEGER DEFAULT 0,
    jobs_drafted INTEGER DEFAULT 0,
    emails_checked INTEGER DEFAULT 0,
    replies_drafted INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- ============================================
-- 6. INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX IF NOT EXISTS idx_job_applications_user_status ON job_applications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_job_applications_gmail_thread ON job_applications(gmail_thread_id);
CREATE INDEX IF NOT EXISTS idx_email_threads_user ON email_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_email_threads_job ON email_threads(job_application_id);
CREATE INDEX IF NOT EXISTS idx_campaign_runs_user ON campaign_runs(user_id);

-- ============================================
-- 7. UPDATED_AT TRIGGERS
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_job_applications_updated_at ON job_applications;
CREATE TRIGGER update_job_applications_updated_at
    BEFORE UPDATE ON job_applications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_email_threads_updated_at ON email_threads;
CREATE TRIGGER update_email_threads_updated_at
    BEFORE UPDATE ON email_threads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_gmail_tokens_updated_at ON user_gmail_tokens;
CREATE TRIGGER update_user_gmail_tokens_updated_at
    BEFORE UPDATE ON user_gmail_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 8. ROW LEVEL SECURITY (Optional but Recommended)
-- ============================================

ALTER TABLE user_gmail_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_runs ENABLE ROW LEVEL SECURITY;

-- For service role access (used by backend)
CREATE POLICY "Service role full access on user_gmail_tokens" ON user_gmail_tokens
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on email_threads" ON email_threads
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on campaign_runs" ON campaign_runs
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- DONE! Run this migration in Supabase SQL Editor
-- ============================================
