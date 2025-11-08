-- Migration 011: Ajout du champ is_virtual sur pole et service
-- Date: 2025-11-07

ALTER TABLE pole ADD COLUMN is_virtual BOOLEAN DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_pole_is_virtual ON pole(is_virtual);

ALTER TABLE service ADD COLUMN is_virtual BOOLEAN DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_service_is_virtual ON service(is_virtual);
