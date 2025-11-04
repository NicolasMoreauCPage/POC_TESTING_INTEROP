-- Migration 003: Add 'type' column to 'mouvement' table and backfill from trigger_event
ALTER TABLE mouvement ADD COLUMN type TEXT;
-- Backfill type from trigger_event when available (e.g., A01 -> ADT^A01)
UPDATE mouvement SET type = 'ADT^' || trigger_event WHERE trigger_event IS NOT NULL AND (type IS NULL OR type = '');
