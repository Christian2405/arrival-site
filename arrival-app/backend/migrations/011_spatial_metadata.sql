-- Spatial Intelligence — Structured Metadata
-- Adds task_type, environment fields to sessions + sequences for ML labeling

ALTER TABLE spatial_sessions ADD COLUMN IF NOT EXISTS task_type TEXT;
ALTER TABLE spatial_sessions ADD COLUMN IF NOT EXISTS environment_type TEXT;     -- indoor/outdoor
ALTER TABLE spatial_sessions ADD COLUMN IF NOT EXISTS environment_setting TEXT;  -- residential/commercial/industrial
ALTER TABLE spatial_sessions ADD COLUMN IF NOT EXISTS environment_space TEXT;    -- attic/panel/rooftop/etc

ALTER TABLE spatial_sequences ADD COLUMN IF NOT EXISTS task_type TEXT;

CREATE INDEX IF NOT EXISTS idx_spatial_sessions_task_type ON spatial_sessions(task_type);
CREATE INDEX IF NOT EXISTS idx_spatial_sessions_env ON spatial_sessions(environment_type);
