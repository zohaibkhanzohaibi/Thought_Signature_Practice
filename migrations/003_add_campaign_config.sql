-- ============================================
-- Migration: Fix schema for campaigns feature
-- ============================================
-- Run this in Supabase SQL Editor

-- ============================================
-- PART 1: Update agent_states table
-- ============================================

-- Add config column (JSONB for campaign settings)
ALTER TABLE agent_states ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}'::jsonb;

-- Add history column (JSONB array for search history)
ALTER TABLE agent_states ADD COLUMN IF NOT EXISTS history JSONB DEFAULT '[]'::jsonb;

-- Create index on config for faster queries
CREATE INDEX IF NOT EXISTS idx_agent_states_config ON agent_states USING GIN (config);

-- ============================================
-- PART 2: Update campaign_runs table
-- ============================================

-- Add agent_state_id column to link runs to campaigns
ALTER TABLE campaign_runs ADD COLUMN IF NOT EXISTS agent_state_id UUID REFERENCES agent_states(id) ON DELETE CASCADE;

-- Add run_type column
ALTER TABLE campaign_runs ADD COLUMN IF NOT EXISTS run_type TEXT DEFAULT 'search';

-- Add jobs_found and jobs_applied columns (different from jobs_scouted/jobs_tailored)
ALTER TABLE campaign_runs ADD COLUMN IF NOT EXISTS jobs_found INTEGER DEFAULT 0;
ALTER TABLE campaign_runs ADD COLUMN IF NOT EXISTS jobs_applied INTEGER DEFAULT 0;

-- Make campaign_day optional (NULL for search runs)
ALTER TABLE campaign_runs ALTER COLUMN campaign_day DROP NOT NULL;

-- Create index on agent_state_id
CREATE INDEX IF NOT EXISTS idx_campaign_runs_agent_state ON campaign_runs(agent_state_id);

-- ============================================
-- PART 3: Reload schema cache
-- ============================================
NOTIFY pgrst, 'reload schema';
