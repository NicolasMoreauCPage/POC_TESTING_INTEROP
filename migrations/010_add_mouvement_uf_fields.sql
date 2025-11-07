-- Migration 010: Ajout des champs UF et nature au modèle Mouvement
-- Date: 2025-11-06

ALTER TABLE mouvement ADD COLUMN uf_hebergement TEXT;
ALTER TABLE mouvement ADD COLUMN uf_medicale TEXT;
ALTER TABLE mouvement ADD COLUMN uf_soins TEXT;

ALTER TABLE mouvement ADD COLUMN movement_nature TEXT;

CREATE INDEX IF NOT EXISTS idx_mouvement_nature ON mouvement(movement_nature);
CREATE INDEX IF NOT EXISTS idx_mouvement_uf_medicale ON mouvement(uf_medicale);
CREATE INDEX IF NOT EXISTS idx_mouvement_uf_hebergement ON mouvement(uf_hebergement);
CREATE INDEX IF NOT EXISTS idx_mouvement_uf_soins ON mouvement(uf_soins);
