-- ============================================
-- FRESH DATABASE SETUP - Run in Supabase SQL Editor
-- This drops all existing tables and creates everything fresh
-- ============================================

-- STEP 1: DROP EVERYTHING
DROP TABLE IF EXISTS campaign_runs CASCADE;
DROP TABLE IF EXISTS email_threads CASCADE;
DROP TABLE IF EXISTS user_gmail_tokens CASCADE;
DROP TABLE IF EXISTS job_applications CASCADE;
DROP TABLE IF EXISTS agent_states CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;

-- ============================================
-- STEP 2: CREATE PROFILES TABLE
-- ============================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    linkedin_url TEXT,
    github_username TEXT,
    summary TEXT,
    master_resume_url TEXT,
    parsed_resume JSONB DEFAULT '{}'::jsonb,
    portfolio_data JSONB DEFAULT '{}'::jsonb,
    contact_info JSONB DEFAULT '{}'::jsonb,
    skills TEXT[] DEFAULT '{}',
    experience_years INTEGER DEFAULT 0,
    preferred_locations TEXT[] DEFAULT '{}',
    target_roles TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- STEP 3: CREATE AGENT_STATES TABLE (Thought Signatures)
-- ============================================
CREATE TABLE agent_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    campaign_id INTEGER,
    thought_signature BYTEA,
    last_search_query TEXT,
    jobs_found_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, campaign_id)
);

-- ============================================
-- STEP 4: CREATE JOB_APPLICATIONS TABLE
-- ============================================
CREATE TABLE job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    campaign_id INTEGER,
    company TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_url TEXT,
    job_description TEXT,
    location TEXT,
    salary_range TEXT,
    posted_date TEXT,
    status TEXT DEFAULT 'scouted' CHECK (status IN ('scouted', 'analyzing', 'tailored', 'drafted', 'sent', 'replied', 'interview', 'offer', 'rejected', 'withdrawn')),
    jd_analysis JSONB DEFAULT '{}'::jsonb,
    tailored_resume JSONB DEFAULT '{}'::jsonb,
    cover_email TEXT,
    resume_pdf_path TEXT,
    gmail_draft_id TEXT,
    gmail_thread_id TEXT,
    gmail_message_id TEXT,
    company_email TEXT,
    match_score INTEGER DEFAULT 0,
    applied_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- STEP 5: CREATE USER_GMAIL_TOKENS TABLE
-- ============================================
CREATE TABLE user_gmail_tokens (
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
-- STEP 6: CREATE EMAIL_THREADS TABLE
-- ============================================
CREATE TABLE email_threads (
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
-- STEP 7: CREATE CAMPAIGN_RUNS TABLE
-- ============================================
CREATE TABLE campaign_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    campaign_id INTEGER,
    campaign_day INTEGER NOT NULL,
    jobs_scouted INTEGER DEFAULT 0,
    jobs_tailored INTEGER DEFAULT 0,
    jobs_drafted INTEGER DEFAULT 0,
    emails_checked INTEGER DEFAULT 0,
    replies_drafted INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    summary TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- ============================================
-- STEP 8: INDEXES
-- ============================================
CREATE INDEX idx_job_applications_user_status ON job_applications(user_id, status);
CREATE INDEX idx_job_applications_gmail_thread ON job_applications(gmail_thread_id);
CREATE INDEX idx_email_threads_user ON email_threads(user_id);
CREATE INDEX idx_email_threads_job ON email_threads(job_application_id);
CREATE INDEX idx_campaign_runs_user ON campaign_runs(user_id);
CREATE INDEX idx_agent_states_user ON agent_states(user_id);

-- ============================================
-- STEP 9: UPDATED_AT TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_applications_updated_at
    BEFORE UPDATE ON job_applications FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_threads_updated_at
    BEFORE UPDATE ON email_threads FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_gmail_tokens_updated_at
    BEFORE UPDATE ON user_gmail_tokens FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- STEP 10: ROW LEVEL SECURITY
-- ============================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_gmail_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_runs ENABLE ROW LEVEL SECURITY;

-- Service role full access policies
CREATE POLICY "Service role full access on profiles" ON profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on agent_states" ON agent_states FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on job_applications" ON job_applications FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on user_gmail_tokens" ON user_gmail_tokens FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on email_threads" ON email_threads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on campaign_runs" ON campaign_runs FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- ✅ DONE! All tables created successfully
-- ============================================
