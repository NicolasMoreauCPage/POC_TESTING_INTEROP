-- Migration: Add patient birth address and identity reliability fields
-- Date: 2024
-- Description: 
--   - Ajout champs adresse de naissance (5 colonnes)
--   - Ajout champs état de l'identité PID-32 (3 colonnes)
--   - Ajout champ country pour adresse d'habitation
--   - Ajout contrainte UNIQUE sur table Identifier

-- =====================================================================
-- PARTIE 1: Nouveaux champs Patient
-- =====================================================================

-- Adresse d'habitation: ajout country
ALTER TABLE patient ADD COLUMN country TEXT;

-- Adresse de naissance (5 champs)
ALTER TABLE patient ADD COLUMN birth_address TEXT;
ALTER TABLE patient ADD COLUMN birth_city TEXT;
ALTER TABLE patient ADD COLUMN birth_state TEXT;
ALTER TABLE patient ADD COLUMN birth_postal_code TEXT;
ALTER TABLE patient ADD COLUMN birth_country TEXT;

-- État de l'identité (PID-32) - 3 champs
ALTER TABLE patient ADD COLUMN identity_reliability_code TEXT;
ALTER TABLE patient ADD COLUMN identity_reliability_date TIMESTAMP;
ALTER TABLE patient ADD COLUMN identity_reliability_source TEXT;

-- =====================================================================
-- PARTIE 2: Contrainte UNIQUE sur Identifier
-- =====================================================================

-- Contrainte: Dans un même système (system + oid), un identifiant ne peut
-- être utilisé que par un seul patient
CREATE UNIQUE INDEX idx_identifier_unique_per_system 
ON identifier(value, system, oid) 
WHERE status = 'active' AND patient_id IS NOT NULL;

-- Note: L'index partiel (WHERE status='active') permet de garder l'historique
-- des identifiants inactifs sans violation de contrainte

-- =====================================================================
-- ROLLBACK (en cas de besoin)
-- =====================================================================

-- Pour annuler cette migration:
--
-- DROP INDEX IF EXISTS idx_identifier_unique_per_system;
-- ALTER TABLE patient DROP COLUMN identity_reliability_source;
-- ALTER TABLE patient DROP COLUMN identity_reliability_date;
-- ALTER TABLE patient DROP COLUMN identity_reliability_code;
-- ALTER TABLE patient DROP COLUMN birth_country;
-- ALTER TABLE patient DROP COLUMN birth_postal_code;
-- ALTER TABLE patient DROP COLUMN birth_state;
-- ALTER TABLE patient DROP COLUMN birth_city;
-- ALTER TABLE patient DROP COLUMN birth_address;
-- ALTER TABLE patient DROP COLUMN country;

-- =====================================================================
-- VÉRIFICATION POST-MIGRATION
-- =====================================================================

-- Compter patients avec nouvelles colonnes (doivent être NULL initialement)
-- SELECT 
--   COUNT(*) as total_patients,
--   COUNT(country) as has_country,
--   COUNT(birth_address) as has_birth_address,
--   COUNT(identity_reliability_code) as has_identity_code
-- FROM patient;

-- Vérifier la contrainte sur Identifier
-- SELECT * FROM sqlite_master WHERE type='index' AND name='idx_identifier_unique_per_system';
