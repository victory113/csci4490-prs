# Patient Record System (PRS) — Version 2

Version 2 corrects, refactors and optimizes the Version 1 implementation in
`../v1`, addressing the weaknesses identified during the group's code analysis.
Behaviour required by the Assignment #2 specification is unchanged; no new
features were added.

## Running

```
cd v2
python main.py
```

Python 3.10+, no third-party packages. `prs.db` is created on first run.

| Username | Password | Role |
|---|---|---|
| `frontdesk` | `pass123` | front_desk — register and update patients |
| `clinician` | `pass123` | clinician — add and amend visit notes |
| `admin` | `pass123` | admin — both, plus the audit log |

Passwords are stored as salted PBKDF2-SHA256 hashes. The values above are the
seeded demo passwords, not what is written to the database.

## Module structure

| Module | A3 package | Responsibility |
|---|---|---|
| `main.py` | `prs.ui` | The only module that prints or reads input |
| `services.py` | `prs.patient`, `prs.visit`, `prs.authentication` | Record logic; raises domain errors |
| `repositories.py` | `prs.persistence` | The only module that contains SQL |
| `database.py` | `prs.persistence` | Connection, schema, transactions, password hashing |
| `models.py` | `prs.patient`, `prs.visit` | `Patient`, `VisitNote`, `StaffUser` |
| `ai_categorizer.py` | `prs.ai_integration` | The only module that contacts the AI provider |
| `errors.py` | — | Domain exception hierarchy |

Dependencies are supplied through constructors in `build_application()` in
`main.py`, so services depend on repository objects rather than creating them.

## Patient ID immutability (FR-02, BC-01)

Three separate mechanisms, addressing three different concerns:

| Concern | Mechanism | Location |
|---|---|---|
| Encapsulation | State is private, reached through properties | `Patient.__slots__`, property accessors |
| Immutability | Read-only property plus a `__setattr__` guard | `Patient.patient_id`, `Patient.__setattr__` |
| Uniqueness | `patient_id TEXT PRIMARY KEY` and a monotonic counter | `database.SCHEMA`, `PatientRepository.next_patient_id` |

Menu option **9** demonstrates this: it attempts to change the ID by direct
attribute assignment, by private attribute assignment, and through the service
layer. All three are refused.

IDs come from a `counters` row that only ever increases, so an ID is never
reused even after a record is removed.

## AI categorization (AIR-01, AIR-02)

- The visit note is written to the database **before** any AI call, so an AI
  failure can never prevent a note from being saved.
- `suggest_category()` never raises. A timeout, transport error, unknown
  category, or confidence below 0.6 returns an unavailable `CategorySuggestion`,
  and the interface records `NO_AI_SUGGESTION` in the audit log with the reason.
- A category is stored only through `confirm_category()`, called when a staff
  member accepts the suggestion.
- Only note text is sent to the provider — no Patient ID, name, or other
  identifier.
- With no `PRS_AI_URL` / `PRS_AI_KEY` configured, a clearly labelled keyword
  substitute is used so the application can be demonstrated. It reports its
  source as `keyword_substitute` and is not an AI model.

## Synthetic data only

All patient data used in development and demonstration is synthetic.
