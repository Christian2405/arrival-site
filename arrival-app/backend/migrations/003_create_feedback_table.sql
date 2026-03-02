-- Migration 003: Create feedback table
-- Stores thumbs-up/down feedback from users on AI responses.
-- Used for quality monitoring and model improvement.

CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative')),
    feedback_text TEXT,
    source TEXT,
    conversation_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON public.feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON public.feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON public.feedback(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- Users can insert their own feedback
CREATE POLICY "users_insert_own_feedback"
    ON public.feedback
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can read their own feedback
CREATE POLICY "users_select_own_feedback"
    ON public.feedback
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role can read all feedback (for analytics)
-- Note: service_role key bypasses RLS by default, so no policy needed for backend analytics.
