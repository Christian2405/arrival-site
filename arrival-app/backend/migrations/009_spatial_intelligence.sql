-- Spatial Intelligence Data Capture
-- Run in Supabase SQL Editor

-- 1. Add consent column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS spatial_capture_consent BOOLEAN DEFAULT NULL;

-- 2. Spatial sessions — one per LiveKit room connection
CREATE TABLE IF NOT EXISTS spatial_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_name TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    team_id UUID,
    trade TEXT,
    equipment_type TEXT,
    equipment_brand TEXT,
    equipment_model TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    clip_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spatial_sessions_user ON spatial_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_spatial_sessions_room ON spatial_sessions(room_name);

-- 3. Spatial clips — one per recorded video clip
CREATE TABLE IF NOT EXISTS spatial_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES spatial_sessions(id) ON DELETE CASCADE,
    s3_key TEXT NOT NULL,
    s3_bucket TEXT NOT NULL DEFAULT 'arrival-spatial-data',
    duration_seconds FLOAT,
    frame_count INTEGER,
    resolution TEXT,
    file_size_bytes BIGINT,
    trigger_type TEXT NOT NULL,
    trigger_text TEXT,
    ai_response TEXT,
    monitor_state TEXT,
    status TEXT DEFAULT 'recording',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spatial_clips_session ON spatial_clips(session_id);
CREATE INDEX IF NOT EXISTS idx_spatial_clips_status ON spatial_clips(status);
CREATE INDEX IF NOT EXISTS idx_spatial_clips_trigger ON spatial_clips(trigger_type);

-- 4. Spatial labels — for future annotation/training
CREATE TABLE IF NOT EXISTS spatial_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID REFERENCES spatial_clips(id) ON DELETE CASCADE,
    label_type TEXT NOT NULL,
    label_value TEXT NOT NULL,
    confidence FLOAT,
    frame_offset_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spatial_labels_clip ON spatial_labels(clip_id);
