-- Migration 002: Authentication Schema
-- Run this in Supabase SQL Editor

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- 2. Link Profiles to Users (Optional but recommended for data integrity)
-- If profiles already exist, we might want to link them later or duplicate.
-- For now, let's assume 'id' in profiles matches 'id' in users if we want strict 1:1.
-- However, since profiles are already created with text IDs possibly, we'll keep them loose for now
-- or enforce it in the backend logic that profile.id == user.id.

-- 3. Security Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 4. RLS Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Allow users to read their own data (if authenticated via Supabase Auth, but we are using custom)
-- Since we are doing custom auth, the SERVICE_ROLE key will be used by the backend to access this table.
-- So we just need to ensure the service role has access.
CREATE POLICY "Service role full access on users" ON users
    FOR ALL USING (true) WITH CHECK (true);
