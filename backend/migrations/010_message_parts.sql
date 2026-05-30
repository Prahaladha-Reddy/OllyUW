-- Add parts JSONB column to session_messages.
-- Stores an ordered array of { type, ... } objects capturing text and tool
-- calls interleaved in the exact order they occurred during a response.
-- Old rows keep their content column and render as plain text on the frontend.
ALTER TABLE session_messages ADD COLUMN IF NOT EXISTS parts JSONB;
