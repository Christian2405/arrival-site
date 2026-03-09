-- Migration 006: Enhance queries table for data flywheel
-- Adds mode (text/voice/job), rag_chunks_used (which docs were used), response_time_ms

ALTER TABLE public.queries ADD COLUMN IF NOT EXISTS mode TEXT;
ALTER TABLE public.queries ADD COLUMN IF NOT EXISTS rag_chunks_used JSONB DEFAULT '[]';
ALTER TABLE public.queries ADD COLUMN IF NOT EXISTS response_time_ms INTEGER;

-- Index for analyzing response times by mode
CREATE INDEX IF NOT EXISTS idx_queries_mode ON public.queries (mode);

-- Index for finding queries with RAG usage (for chunk scoring)
CREATE INDEX IF NOT EXISTS idx_queries_has_rag ON public.queries ((rag_chunks_used != '[]'::jsonb))
WHERE rag_chunks_used != '[]'::jsonb;
