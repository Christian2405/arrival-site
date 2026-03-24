-- Spatial Intelligence v2: Sequences + Rich Labels
-- Run in Supabase SQL Editor

-- 1. Add sequence tracking to spatial_clips
ALTER TABLE spatial_clips ADD COLUMN IF NOT EXISTS sequence_id UUID;
ALTER TABLE spatial_clips ADD COLUMN IF NOT EXISTS sequence_order INTEGER DEFAULT 0;
ALTER TABLE spatial_clips ADD COLUMN IF NOT EXISTS parent_clip_id UUID REFERENCES spatial_clips(id);
ALTER TABLE spatial_clips ADD COLUMN IF NOT EXISTS outcome TEXT;  -- 'success', 'failed', 'unknown', 'abandoned'
ALTER TABLE spatial_clips ADD COLUMN IF NOT EXISTS workflow_stage TEXT;  -- 'inspection', 'diagnosis', 'repair', 'verify', 'cleanup'

CREATE INDEX IF NOT EXISTS idx_spatial_clips_sequence ON spatial_clips(sequence_id);

-- 2. Enrich spatial_labels with structured label types
-- Existing table: id, clip_id, label_type, label_value, confidence, frame_offset_seconds
-- label_type values:
--   'semantic'   - what the user asked ("what's this part", "why isn't this working")
--   'equipment'  - what they pointed at (brand, model, type from vision)
--   'action'     - what they did (removed panel, tested voltage, replaced part)
--   'state'      - before/after (broken, working, in_progress)
--   'outcome'    - did it work (success, failed, unknown)
--   'workflow'   - where in task sequence (inspection, diagnosis, repair, verify)
--   'object'     - detected objects from proactive monitor

-- 3. Spatial sequences table — groups clips into jobs/workflows
CREATE TABLE IF NOT EXISTS spatial_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES spatial_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    task_description TEXT,
    equipment_type TEXT,
    equipment_brand TEXT,
    equipment_model TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    clip_count INTEGER DEFAULT 0,
    outcome TEXT,  -- overall job outcome
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spatial_sequences_session ON spatial_sequences(session_id);
CREATE INDEX IF NOT EXISTS idx_spatial_sequences_user ON spatial_sequences(user_id);
