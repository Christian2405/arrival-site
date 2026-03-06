-- Migration 004: Enhance feedback table for the data flywheel
-- Adds columns for admin corrections and knowledge base promotion.
-- Run via Supabase SQL editor.

ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS mode TEXT;
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS reviewed BOOLEAN DEFAULT FALSE;
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS correction TEXT;
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS promoted_to_knowledge BOOLEAN DEFAULT FALSE;

-- Index for admin review queries (unreviewed negative feedback)
CREATE INDEX IF NOT EXISTS idx_feedback_unreviewed
    ON public.feedback(reviewed, created_at DESC)
    WHERE reviewed = FALSE;

-- Index for correction cache refresh (negative + has correction)
CREATE INDEX IF NOT EXISTS idx_feedback_corrections
    ON public.feedback(rating, created_at DESC)
    WHERE rating = 'negative' AND correction IS NOT NULL;
