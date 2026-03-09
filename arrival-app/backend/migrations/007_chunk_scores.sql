-- Migration 007: RAG chunk scoring table for data flywheel
-- Tracks which Pinecone chunks get positive/negative feedback
-- Used to boost good chunks and flag bad ones

CREATE TABLE IF NOT EXISTS public.chunk_scores (
    chunk_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'global_knowledge',
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    net_score INTEGER GENERATED ALWAYS AS (positive_count - negative_count) STORED,
    last_updated TIMESTAMPTZ DEFAULT now()
);

-- Index for finding chunks that need review (net negative)
CREATE INDEX IF NOT EXISTS idx_chunk_scores_negative
ON public.chunk_scores (net_score)
WHERE net_score < -2;

-- Index for finding chunks to boost (strong positive)
CREATE INDEX IF NOT EXISTS idx_chunk_scores_positive
ON public.chunk_scores (net_score)
WHERE positive_count >= 5;

-- RLS: service role only (backend manages this table)
ALTER TABLE public.chunk_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on chunk_scores"
ON public.chunk_scores
FOR ALL
USING (auth.role() = 'service_role');
