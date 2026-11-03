# Patient Record System (PRS) — Version 1

Initial implementation generated with GenAI from the Assignment #2 requirements
specification and the Assignment #3 4+1 architecture.

**This is Version 1 and is preserved unmodified.** Corrections, refactoring and
optimization are applied in `../v2`.

## Requirements implemented

| Area | Requirements |
|---|---|
| Patient management | FR-01, FR-02, FR-03, FR-04, FR-05 |
| Visit notes | FR-06, FR-07 |
| AI categorization | FR-08, FR-09, AIR-01, AIR-02 |
| Audit trail | FR-10 |
| Authentication / roles | NFR-02 |

## Requirements

- Python 3.10 or newer. No third-party packages — persistence uses the
  standard-library `sqlite3` module.

## Running the application

```
cd v1
python main.py
```

The database file `prs.db` is created automatically in the working directory on
first run, and the data persists across restarts.

## Demo accounts

Seeded automatically on first run.

| Username | Password | Role | Can do |
|---|---|---|---|
| `frontdesk` | `pass123` | front_desk | Register and update patients |
| `clinician` | `pass123` | clinician | Add visit notes, amend notes |
| `admin` | `pass123` | admin | Both |

## Suggested walkthrough

1. `1` — log in as `frontdesk`
2. `2` — register a patient; the system assigns a Patient ID such as `P-000001`
3. `3` — look the patient up by that ID
4. `4` — update `phone`; the previous value is written to the audit log
5. `9` then `1` — log in as `clinician`
6. `5` — add a visit note, for example "persistent cough and chest congestion";
   a category is suggested and you accept or reject it
7. `6` — view the visit history, most recent first
8. `3` — search `P-999999` to see the not-found message (FR-04)
9. `8` — view the audit log

## AI categorization

`ai_categorizer.py` calls an external service when `PRS_AI_URL` and `PRS_AI_KEY`
are set in the environment, with a 2-second timeout and a confidence threshold
of 0.6 (AIR-02).

When no service is configured, or the call fails, the adapter falls back to
`keyword_fallback()`. **That fallback is a temporary test substitute, not an AI
model**, and is labelled as such in the source.

In both cases a suggestion is only displayed. A category is stored only after a
staff member explicitly accepts it (AIR-01), and the visit note is saved to the
database *before* any AI call is made, so an AI failure can never prevent a note
from being recorded (NFR-03, AIR-02).

## Synthetic data only

All patient data used in development and demonstration is synthetic.
