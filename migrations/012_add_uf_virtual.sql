-- Migration 012: add is_virtual column to unitefonctionnelle if missing
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- Check existing columns
CREATE TEMP TABLE __tmp_cols AS SELECT name FROM pragma_table_info('unitefonctionnelle');

-- Add column if not exists
INSERT INTO __tmp_cols SELECT 'is_virtual' WHERE NOT EXISTS (SELECT 1 FROM __tmp_cols WHERE name='is_virtual');

-- We can't branch in pure SQL easily; attempt ALTER and ignore error if already exists.
-- SQLite prior to 3.35 has limited IF NOT EXISTS support. Safe approach: try add.
ALTER TABLE unitefonctionnelle ADD COLUMN is_virtual INTEGER DEFAULT 0;

DROP TABLE __tmp_cols;
COMMIT;
PRAGMA foreign_keys=ON;
