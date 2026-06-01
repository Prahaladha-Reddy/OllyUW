ALTER TABLE connections
  ADD CONSTRAINT connections_user_provider_unique UNIQUE (user_id, provider);
