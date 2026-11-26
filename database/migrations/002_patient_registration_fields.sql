BEGIN;

ALTER TABLE patients
    ADD COLUMN IF NOT EXISTS date_of_birth DATE,
    ADD COLUMN IF NOT EXISTS known_eye_conditions TEXT,
    ADD COLUMN IF NOT EXISTS family_history_glaucoma BOOLEAN,
    ADD COLUMN IF NOT EXISTS diabetes BOOLEAN;

COMMIT;