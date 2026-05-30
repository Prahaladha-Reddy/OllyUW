-- Store tool calls alongside the assistant message so they survive page refreshes.
-- Each element: { id, tool, args, status, output }
ALTER TABLE session_messages ADD COLUMN IF NOT EXISTS tool_calls JSONB;
