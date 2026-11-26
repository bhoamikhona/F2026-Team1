# Back end (API)

The API the frontend calls, built with FastAPI.

The model is currently a stand-in. `mock_model.py` returns made-up scores
(the same photo always gets the same scores) and heatmaps marked "MOCK".
Login, patients, uploads, the photo quality check, screenings, history,
the clinician dashboard and PDF exports are real. When the trained model
is ready, the model implementation will be replaced while preserving the
existing API contract.

## Run it

From the repo folder, with the virtual environment active (see Setup in
the main README):

    uvicorn backend.main:app --reload

The API runs at http://localhost:8000. Every endpoint is listed at
http://localhost:8000/docs, where you can also try each one.

It uses the Supabase database and Storage set in `.env` (see Run the app in
the main README). Locally you work on the same data as the live prototype,
so sign in with the demo account in the main README and only add made-up
patients.

To set up a new, empty database from `database/schema.sql`, see "New database"
in the main README.

## Calling it from the frontend

- Add `credentials: "include"` to every fetch. Login sets a session cookie.
- The Vite dev server (http://localhost:5173) is allowed. Add other addresses
  with `DUAL_CORS_ORIGINS`, separated by commas.
- Photo and heatmap URLs come back as paths, for example `/heatmaps/HM-0001`.
  Put `http://localhost:8000` in front.
- Errors come back with a `detail` field: 401 not signed in, 403 another
  user's personalized records, 404 not found, 409 not allowed (for example
  screening a photo that failed the check), 422 a missing or wrong field.
- Thresholds are placeholders until the trained model replaces the mock.
  Read them from `GET /model` or from each condition in a screening;
  don't hard-code them.
- When a condition is `uncertain`, Results shows no score. The Screening
  record still shows both scores.

## Endpoints

| Method and path                                               | Screen                               | Returns or does                                                            |
| ------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------- |
| POST /auth/login                                              | Login                                | The user; sets the session cookie                                          |
| POST /auth/logout                                             | Sign out                             | Ends the session                                                           |
| GET /auth/me                                                  | Header                               | The signed-in user                                                         |
| GET /patients?query=                                          | New screening, History filter        | All patients, sorted by last name, with screening summaries                |
| GET /patients/next-id                                         | Add patient                          | Preview of the next patient ID                                             |
| POST /patients                                                | Add patient                          | Registers a patient under the signed-in clinician                          |
| GET /patients/{id}                                            | Patient page                         | Patient, last encounter, latest screening per eye                          |
| GET /patients/{id}/screenings?date=today                      | Upload (today's visit), Patient page | Screenings, newest first                                                   |
| GET /patients/{id}/export                                     | Patient page: Export Dossier         | PDF                                                                        |
| POST /images (form: file, patient_id, eye)                    | New screening                        | The image with quality_status and quality_reason                           |
| GET /images/{id}                                              | Results                              | 512 x 512 preprocessed photo                                               |
| GET /images/{id}/original                                     | Screening record                     | Original-resolution stored photo                                           |
| DELETE /images/{id}                                           | Photo quality failed: Retake         | Discards an unscreened photo                                               |
| POST /screenings                                              | Screen this photo, Skip eye          | Screening with results and heatmaps, or a skipped-eye record               |
| GET /screenings?query=&patient=&date=&eye=&result=            | History                              | Screenings, newest first, with the clinician who ran each one              |
| GET /screenings/{id}                                          | Results, Screening record            | Screening, patient, image, results, heatmaps, model version                |
| GET /screenings/{id}/export                                   | Screening record: Export summary     | PDF                                                                        |
| GET /heatmaps/{id}                                            | Results, Screening record            | Heatmap image                                                              |
| GET /users/{id}/patients?query=                               | My Patients                          | Patients the user added or screened, with the latest status per eye        |
| GET /users/{id}/screenings?query=&patient=&date=&eye=&result= | Dashboard                            | Screenings the user ran, newest first                                      |
| GET /users/{id}/summary                                       | Dashboard                            | Today's counts, patients to follow up, eyes to rescreen and weekly results |
| GET /model                                                    | About, Screening record              | Model version and thresholds                                               |
| GET /health                                                   | None (server check, no sign-in)      | `{"status": "ok"}`                                                         |

To skip an eye, send `POST /screenings` with
`{"patient_id": "P-001", "eye": "left", "skipped": true, "skip_reason": "..."}`.

## Patient registration

`POST /patients` accepts the patient's full name, sex, date of birth
or age, and the following optional fields:

- `phone`
- `email`
- `known_eye_conditions`
- `family_history_glaucoma`
- `diabetes`

When a date of birth is supplied in `YYYY-MM-DD` format, the server
calculates the patient's age automatically. Existing clients can still
provide age instead.

Medical history fields are nullable. For boolean fields, `true` means yes,
`false` means no, and `null` means unknown or not provided.

The server generates the patient ID and sets `created_by` to the signed-in
clinician's ID. Patients can be registered without starting a screening
and appear in the clinician's My Patients list immediately.

`POST /patients` returns the newly created patient directly.
`GET /patients/{id}` returns a detail object containing `patient`,
`last_encounter` and `latest`.

## Patient summaries and dashboard

Both `/patients` and `/users/{id}/patients` return patient summaries with:

- `last_screening_at`: timestamp of the latest screening record.
- `screening_count`: number of screening records, including skipped eyes.
- `latest_right` and `latest_left`: latest overall result per eye.
- `right_status` and `left_status`: detailed status per eye.

The eye statuses are:

| Status         | Meaning                                 |
| -------------- | --------------------------------------- |
| `not_screened` | No screening record exists for the eye  |
| `skipped`      | The latest screening record was skipped |
| `no_concern`   | No concern was found                    |
| `refer`        | Refer without an Uncertain condition    |
| `uncertain`    | At least one condition was Uncertain    |

The existing overall result fields remain unchanged: an Uncertain
condition still produces an overall Refer result.

Dashboard activity counts and recent screenings are specific to the
signed-in clinician. Counts represent individual eye screenings, not
unique patients.

Follow-up and rescreen lists consider the latest screening records for
all patients the clinician added or screened, regardless of which
clinician performed the screening.

A skipped eye is removed from the rescreen list once a newer completed
screening exists for that eye. Never-screened eyes are not treated as
skipped eyes.

Weekly results cover today and the preceding six days. Skipped eyes
are excluded from completed screening counts.

## Rules the server enforces

- The model only runs on a photo that passed the quality check, was uploaded
  for the same patient and eye, and has not been screened before.
- Per condition: a score within 0.05 of the threshold, on either side, is
  `uncertain` (too close to call). Otherwise a score at or above the threshold
  is `refer` and below it is `no_concern`. For cataract (threshold 0.35):
  0.32 and 0.38 are `uncertain`, 0.45 is `refer`, 0.20 is `no_concern`.
  These numbers are placeholders. The real thresholds and margins were frozen
  in Task 12 (`results/calibration/frozen_settings.json`) and come in with the
  trained model.
- Per eye: `refer` if either condition is `refer` or `uncertain`, otherwise
  `no_concern`.
- The same eye can be screened again with a new photo, for a follow-up visit
  or a retake. Every screening is kept; the newest one per eye is shown on
  the patient page.
- The same photo is never screened twice for the same patient and eye,
  even if it is uploaded again or "Screen this photo" is clicked twice.
  The second try gets 409.
- A skipped eye requires a reason.
- Patient age must be between 0 and 120. Future dates of birth are rejected.
- Application data endpoints require a valid session. Passwords are stored
  hashed.
- Only clinic staff have accounts; patients never log in. Every signed-in
  user can see every patient through the general clinic endpoints.
- The `/users/{id}` endpoints only return the signed-in user's personalized
  records. Any other ID gets 403.
- Each newly registered patient records who added them (`created_by`).
  A user's patients are the ones they added or have screened.

## Database migrations

`database/schema.sql` is for initializing a new, empty database only.
Do not run it against an existing database.

For existing databases, apply any pending migrations in
`database/migrations/` in order using the Supabase SQL Editor.

| Migration                             | Purpose                                                                           |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `001_patients_created_by.sql`         | Adds patient ownership and indexes for clinician-specific queries                 |
| `002_patient_registration_fields.sql` | Adds date of birth, known eye conditions, family history of glaucoma and diabetes |

The ownership migration uses the earliest screening to backfill
`created_by` for historical patients without a recorded creator.
Historical patients without screenings remain unassigned if their
creator is unknown.

New patients receive `created_by` directly from the signed-in clinician
when registered.

The registration fields migration adds nullable columns without
overwriting existing patient information.

Both migrations are reflected in `database/schema.sql`.

## Files

- `main.py` the endpoints
- `service.py` what each endpoint does (database, files, quality check, model)
- `mock_model.py` placeholder scores, calibration and heatmaps
- `results.py` turns scores into No concern, Refer or Uncertain
- `auth.py` login, password hashing and sessions
- `reports.py` the PDF exports
- `seed.py` the demo users, patients and screenings
- `db.py` the PostgreSQL connection and readable IDs (P-001, IMG-0001)
- `schemas.py` request and response shapes (shown on /docs)
- `../database/schema.sql` the database tables for new databases
- `../database/migrations/` schema changes for existing databases
- `../tests/test_api.py` API integration and regression tests

## Tests

From the repo folder, with the virtual environment active:

    python -m pytest tests/test_api.py

The tests cover authentication, patient registration, medical history,
patient ownership, image handling, screenings, PDF exports, clinician-specific
endpoints, dashboard counts and rescreen logic.

They require `.env` and connect to the PostgreSQL database specified by
`DATABASE_URL`. Temporary test records are created and removed through
scoped cleanup. Supabase Storage is mocked in memory, so no test images
or heatmaps are uploaded.

An isolated test database is recommended because the tests perform real
database writes and cleanup is not guaranteed if execution is interrupted.
