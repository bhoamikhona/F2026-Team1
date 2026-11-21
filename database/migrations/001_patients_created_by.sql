ALTER TABLE patients
    ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users (id);

UPDATE patients p
SET created_by = (
    SELECT s.created_by
    FROM screenings s
    WHERE s.patient_id = p.id
    ORDER BY s.created_at, s.id
    LIMIT 1
)
WHERE p.created_by IS NULL;

UPDATE patients
SET created_by = (
    SELECT id
    FROM users
    WHERE role = 'clinician'
    ORDER BY id
    LIMIT 1
)
WHERE created_by IS NULL;

CREATE INDEX IF NOT EXISTS patients_created_by_idx ON patients (created_by);
CREATE INDEX IF NOT EXISTS screenings_created_by_idx ON screenings (created_by);