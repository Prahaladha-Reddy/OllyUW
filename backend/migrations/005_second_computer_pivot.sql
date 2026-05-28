CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS computers (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status      TEXT        NOT NULL DEFAULT 'sleeping' CHECK (status IN ('sleeping', 'online')),
  last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id)
);

ALTER TABLE computers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_computers" ON computers;
CREATE POLICY "users_own_computers" ON computers
  FOR ALL USING (auth.uid() = user_id);

INSERT INTO computers (user_id, status, last_active)
SELECT DISTINCT legacy.user_id, 'sleeping', NOW()
FROM (
  SELECT user_id FROM projects
  UNION
  SELECT user_id FROM files
  UNION
  SELECT user_id FROM conversations
  UNION
  SELECT user_id FROM messages
) AS legacy
WHERE legacy.user_id IS NOT NULL
ON CONFLICT (user_id) DO NOTHING;

ALTER TABLE files
  ADD COLUMN IF NOT EXISTS computer_id UUID REFERENCES computers(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS parent_folder_id UUID REFERENCES files(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS file_type TEXT,
  ADD COLUMN IF NOT EXISTS automation_trigger_id TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE files
SET
  computer_id = computers.id,
  name = COALESCE(files.name, files.original_name),
  file_type = COALESCE(files.file_type, 'file'),
  updated_at = COALESCE(files.updated_at, files.created_at, NOW())
FROM computers
WHERE computers.user_id = files.user_id
  AND (
    files.computer_id IS NULL
    OR files.name IS NULL
    OR files.file_type IS NULL
  );

ALTER TABLE files
  ALTER COLUMN project_id DROP NOT NULL,
  ALTER COLUMN storage_path DROP NOT NULL,
  ALTER COLUMN original_name DROP NOT NULL,
  ALTER COLUMN name SET NOT NULL,
  ALTER COLUMN file_type SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'files_file_type_check'
  ) THEN
    ALTER TABLE files
      ADD CONSTRAINT files_file_type_check CHECK (file_type IN ('file', 'folder'));
  END IF;
END $$;

ALTER TABLE files ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_files" ON files;
CREATE POLICY "users_own_files" ON files
  FOR ALL USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS files_user_id_parent_folder_idx
  ON files (user_id, parent_folder_id, file_type, name);

DROP TRIGGER IF EXISTS files_updated_at ON files;
CREATE TRIGGER files_updated_at
  BEFORE UPDATE ON files
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE IF NOT EXISTS vault_items (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  item_type      TEXT        NOT NULL CHECK (item_type IN ('cookie', 'credential', 'api_key', 'bookmark', 'local_storage')),
  key            TEXT        NOT NULL,
  encrypted_data TEXT        NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE vault_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_vault_items" ON vault_items;
CREATE POLICY "users_own_vault_items" ON vault_items
  FOR ALL USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS vault_items_user_id_idx
  ON vault_items (user_id, item_type, key);

DROP TRIGGER IF EXISTS vault_items_updated_at ON vault_items;
CREATE TRIGGER vault_items_updated_at
  BEFORE UPDATE ON vault_items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE IF NOT EXISTS connections (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  composio_account_id TEXT        NOT NULL,
  provider            TEXT        NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE connections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_connections" ON connections;
CREATE POLICY "users_own_connections" ON connections
  FOR ALL USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS connections_user_id_provider_idx
  ON connections (user_id, provider);

DROP TRIGGER IF EXISTS computers_updated_at ON computers;
CREATE TRIGGER computers_updated_at
  BEFORE UPDATE ON computers
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
