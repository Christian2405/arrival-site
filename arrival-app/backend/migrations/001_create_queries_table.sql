-- ============================================
-- Migration: Create queries table for Team Activity tracking
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================

CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    response TEXT,
    source TEXT,
    confidence TEXT,
    has_image BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast team activity lookups
CREATE INDEX IF NOT EXISTS idx_queries_team_id ON queries(team_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id, created_at DESC);

-- Enable RLS
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;

-- Users can view their own queries
CREATE POLICY "Users can view own queries" ON queries
    FOR SELECT USING (user_id = auth.uid());

-- Team members can view all team queries
CREATE POLICY "Team members can view team queries" ON queries
    FOR SELECT USING (
        team_id IN (
            SELECT team_id FROM team_members
            WHERE user_id = auth.uid() AND status = 'active'
        )
    );

-- Service role can insert (backend uses service role for logging)
-- Note: service role bypasses RLS, so no INSERT policy needed for backend.
-- But for completeness, allow users to insert their own:
CREATE POLICY "Users can insert own queries" ON queries
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- ============================================
-- Also create saved_answers table for future use
-- ============================================

CREATE TABLE IF NOT EXISTS saved_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source TEXT,
    confidence TEXT,
    trade TEXT DEFAULT 'HVAC',
    saved_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_answers_user_id ON saved_answers(user_id, saved_at DESC);

ALTER TABLE saved_answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own saved answers" ON saved_answers
    FOR ALL USING (user_id = auth.uid());
