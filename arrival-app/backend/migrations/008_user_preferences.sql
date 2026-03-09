-- Migration 008: User preferences table (replaces Mem0)
-- Lightweight user-specific memory: preferred units, brands they work on, equipment types

CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    preferred_units TEXT DEFAULT 'imperial',
    common_brands TEXT[] DEFAULT '{}',
    equipment_types TEXT[] DEFAULT '{}',
    notes JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: users can read/write their own preferences
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own preferences"
ON public.user_preferences FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users update own preferences"
ON public.user_preferences FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users insert own preferences"
ON public.user_preferences FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Service role can read all (for backend preference injection)
CREATE POLICY "Service role full access on user_preferences"
ON public.user_preferences FOR ALL
USING (auth.role() = 'service_role');
