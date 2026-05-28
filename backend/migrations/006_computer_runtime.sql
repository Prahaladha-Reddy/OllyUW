ALTER TABLE computers
  ADD COLUMN IF NOT EXISTS runtime_state TEXT NOT NULL DEFAULT 'stopped',
  ADD COLUMN IF NOT EXISTS sandbox_id TEXT,
  ADD COLUMN IF NOT EXISTS snapshot_id TEXT,
  ADD COLUMN IF NOT EXISTS workspace_path TEXT NOT NULL DEFAULT '/home/user/workspace',
  ADD COLUMN IF NOT EXISTS git_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS desktop_host TEXT,
  ADD COLUMN IF NOT EXISTS desktop_port INTEGER,
  ADD COLUMN IF NOT EXISTS last_booted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_paused_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_snapshot_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS error_message TEXT;

UPDATE computers
SET runtime_state = CASE
  WHEN status = 'online' THEN 'running'
  ELSE 'stopped'
END
WHERE runtime_state IS NULL OR runtime_state = '';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'computers_runtime_state_check'
  ) THEN
    ALTER TABLE computers
      ADD CONSTRAINT computers_runtime_state_check
      CHECK (runtime_state IN ('stopped', 'starting', 'running', 'paused', 'error'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS computers_sandbox_id_idx
  ON computers (sandbox_id);
