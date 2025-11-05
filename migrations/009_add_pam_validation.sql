-- Add PAM validation fields to SystemEndpoint and MessageLog
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- SystemEndpoint: add validation controls (receiver side)
ALTER TABLE systemendpoint ADD COLUMN pam_validate_enabled INTEGER DEFAULT 0;
ALTER TABLE systemendpoint ADD COLUMN pam_validate_mode TEXT DEFAULT 'warn';
ALTER TABLE systemendpoint ADD COLUMN pam_profile TEXT DEFAULT 'IHE_PAM_FR';

-- MessageLog: store validation results
ALTER TABLE messagelog ADD COLUMN pam_validation_status TEXT;
ALTER TABLE messagelog ADD COLUMN pam_validation_issues TEXT;

COMMIT;
PRAGMA foreign_keys=on;
