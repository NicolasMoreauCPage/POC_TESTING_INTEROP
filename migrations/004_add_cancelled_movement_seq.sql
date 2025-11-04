-- Add a reference from cancellation movements (A12/A13) to the original movement sequence
ALTER TABLE mouvement ADD COLUMN IF NOT EXISTS cancelled_movement_seq INTEGER;
