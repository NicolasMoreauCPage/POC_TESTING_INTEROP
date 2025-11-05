-- Migration 008: Add entite_juridique_id to identifiernamespace
-- Les namespaces peuvent maintenant être liés à une EJ spécifique (IPP, NDA, etc.)
-- ou rester au niveau GHT (pour les identifiants de structure)

ALTER TABLE identifiernamespace 
ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id);

CREATE INDEX idx_namespace_ej ON identifiernamespace(entite_juridique_id);
