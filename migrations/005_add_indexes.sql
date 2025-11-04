-- Performance indexes for common queries
-- Index for listing movements by venue and time
CREATE INDEX IF NOT EXISTS idx_mouvement_venue_when ON mouvement (venue_id, "when");

-- Index for filtering messages by time and endpoint
CREATE INDEX IF NOT EXISTS idx_message_log_created_endpoint ON message_log (created_at, endpoint_id);
