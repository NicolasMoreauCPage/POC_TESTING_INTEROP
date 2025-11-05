-- Add entite_juridique_id to systemendpoint for hierarchical organization
-- This allows endpoints to be organized by GHT and établissement juridique

ALTER TABLE systemendpoint
ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id);

-- Create index for better query performance
CREATE INDEX idx_systemendpoint_entite_juridique_id ON systemendpoint(entite_juridique_id);
