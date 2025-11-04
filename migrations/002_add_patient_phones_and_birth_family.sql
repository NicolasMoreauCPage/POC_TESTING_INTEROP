-- Migration 002: Ajout champs téléphones multiples et nom de naissance
-- Date: 2025-11-03
-- Description: Ajoute les champs mobile, work_phone et birth_family au modèle Patient
--              pour supporter la gestion multi-valuée des téléphones (PID-13) et noms (PID-5)

-- Ajouter le champ birth_family (nom de naissance / nom de jeune fille)
-- Correspond à la 2e répétition PID-5 avec type L (Legal name at birth)
ALTER TABLE patient ADD COLUMN birth_family VARCHAR;

-- Ajouter les champs pour téléphones multiples
-- PID-13 peut contenir plusieurs répétitions: fixe, mobile, professionnel
ALTER TABLE patient ADD COLUMN mobile VARCHAR;
ALTER TABLE patient ADD COLUMN work_phone VARCHAR;

-- Commentaires pour documentation
COMMENT ON COLUMN patient.birth_family IS 'Nom de naissance (nom de jeune fille) - PID-5 répétition type L';
COMMENT ON COLUMN patient.mobile IS 'Téléphone mobile/cellulaire - PID-13 répétition type CP/CELL';
COMMENT ON COLUMN patient.work_phone IS 'Téléphone professionnel - PID-13 répétition type WP/WORK';
