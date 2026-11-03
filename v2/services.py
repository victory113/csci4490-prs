"""Application services for PRS.

Services contain record logic only. They raise domain errors and return
objects; they never print, never read input, and never build SQL. Their
repositories are supplied by the caller rather than constructed here, which
is what lets the architecture's interfaces be honoured.
"""

from datetime import datetime, timedelta

from ai_categorizer import AICategorizer, CATEGORIES
from database import hash_password
from errors import (AccountLockedError, ImmutableFieldError, NotAuthenticatedError,
                    NoteNotFoundError, PatientNotFoundError, PermissionDeniedError,
                    ValidationError)
from models import Patient, VisitNote, EDITABLE_PATIENT_FIELDS

MAX_FAILED_ATTEMPTS = 5
SESSION_TIMEOUT_MINUTES = 15


class AuthService:
    """Authentication, session expiry and account lockout (NFR-02)."""

    def __init__(self, staff_repository, session_timeout_minutes=SESSION_TIMEOUT_MINUTES):
        self._staff = staff_repository
        self._timeout = timedelta(minutes=session_timeout_minutes)
        self._current_user = None
        self._last_activity = None

    def login(self, username, password):
        row = self._staff.find(username)
        if row is None:
            raise ValidationError("Incorrect username or password.")
        if row["locked"]:
            raise AccountLockedError(
                "This account is locked after repeated failed sign-in attempts.")

        _, expected = hash_password(password, row["password_salt"])
        if expected != row["password_hash"]:
            attempts = row["failed_attempts"] + 1
            locked = attempts >= MAX_FAILED_ATTEMPTS
            self._staff.record_failure(username, attempts, locked)
            if locked:
                raise AccountLockedError(
                    "This account is now locked after "
                    f"{MAX_FAILED_ATTEMPTS} failed sign-in attempts.")
            raise ValidationError("Incorrect username or password.")

        self._staff.reset_failures(username)
        self._current_user = self._staff.to_user(row)
        self._last_activity = datetime.now()
        return self._current_user

    def logout(self):
        self._current_user = None
        self._last_activity = None

    @property
    def current_user(self):
        if self._current_user is None:
            return None
        if datetime.now() - self._last_activity > self._timeout:
            self.logout()
            return None
        return self._current_user

    def require_user(self, action):
        """Return the signed-in user, or raise if absent or not permitted."""
        user = self.current_user
        if user is None:
            raise NotAuthenticatedError("You must sign in first.")
        if not user.has_permission(action):
            raise PermissionDeniedError(
                f"Role '{user.role}' is not permitted to {action.replace('_', ' ')}.")
        self._last_activity = datetime.now()
        return user


class PatientService:
    """Creates, retrieves and updates patient records (FR-01 to FR-05)."""

    def __init__(self, database, patient_repository, audit_repository, auth_service):
        self._db = database
        self._patients = patient_repository
        self._audit = audit_repository
        self._auth = auth_service

    def register_patient(self, name, date_of_birth="", phone="", address="",
                         emergency_contact=""):
        user = self._auth.require_user("register_patient")
        with self._db.transaction() as connection:
            patient_id = self._patients.next_patient_id(connection)
            patient = Patient(patient_id, name, date_of_birth, phone, address,
                              emergency_contact)
            self._patients.insert(connection, patient)
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               "REGISTER_PATIENT", patient_id)
        return patient

    def get_patient(self, patient_id):
        self._auth.require_user("view_patient")
        patient = self._patients.find_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError(patient_id)
        return patient

    def update_patient(self, patient_id, field, value):
        user = self._auth.require_user("update_patient")
        if field == "patient_id":
            raise ImmutableFieldError("Patient ID cannot be changed.")
        if field not in EDITABLE_PATIENT_FIELDS:
            raise ValidationError(f"'{field}' is not an editable field.")
        patient = self._patients.find_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError(patient_id)

        previous_value = getattr(patient, field)
        setattr(patient, field, value)          # validated by the model
        with self._db.transaction() as connection:
            self._patients.update_field(connection, patient_id, field,
                                        getattr(patient, field))
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               f"UPDATE_{field.upper()}", patient_id, str(previous_value))
        return patient


class VisitService:
    """Visit notes, history and amendments (FR-06, FR-07, FR-10, BC-02, BC-03)."""

    def __init__(self, database, visit_repository, patient_repository,
                 audit_repository, auth_service, categorizer=None):
        self._db = database
        self._visits = visit_repository
        self._patients = patient_repository
        self._audit = audit_repository
        self._auth = auth_service
        self._categorizer = categorizer or AICategorizer()

    def add_visit_note(self, patient_id, visit_date, note_text):
        """Save the note. No AI call happens here, so AI cannot block a save."""
        user = self._auth.require_user("add_note")
        if not self._patients.exists(patient_id):
            raise PatientNotFoundError(patient_id)
        note = VisitNote(None, patient_id, visit_date, note_text, user.username)
        with self._db.transaction() as connection:
            note.note_id = self._visits.insert(connection, note)
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               "ADD_NOTE", str(note.note_id))
        return note

    def request_category_suggestion(self, note_text):
        """Ask the adapter for a suggestion. Nothing is stored (AIR-01)."""
        return self._categorizer.suggest_category(note_text)

    def confirm_category(self, note_id, category):
        """Store a category only because a staff member accepted it (AIR-01)."""
        user = self._auth.require_user("confirm_category")
        if category not in CATEGORIES:
            raise ValidationError("Category is outside the permitted list.")
        if self._visits.find_by_id(note_id) is None:
            raise NoteNotFoundError(f"No visit note with id {note_id}.")
        with self._db.transaction() as connection:
            self._visits.set_category(connection, note_id, category)
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               "ACCEPT_CATEGORY", str(note_id))

    def record_no_suggestion(self, note_id, reason):
        """Record that no AI suggestion was available for this note (AIR-02)."""
        user = self._auth.require_user("add_note")
        with self._db.transaction() as connection:
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               "NO_AI_SUGGESTION", str(note_id), reason)

    def get_visit_history(self, patient_id):
        self._auth.require_user("view_patient")
        if not self._patients.exists(patient_id):
            raise PatientNotFoundError(patient_id)
        return self._visits.find_by_patient(patient_id)

    def amend_note(self, original_note_id, visit_date, corrected_text):
        """Add a correction and mark the original superseded; nothing is deleted."""
        user = self._auth.require_user("amend_note")
        original = self._visits.find_by_id(original_note_id)
        if original is None:
            raise NoteNotFoundError(f"No visit note with id {original_note_id}.")
        amendment = VisitNote(None, original.patient_id, visit_date, corrected_text,
                              user.username, amends_note_id=original_note_id)
        with self._db.transaction() as connection:
            amendment.note_id = self._visits.insert(connection, amendment)
            self._visits.mark_superseded(connection, original_note_id)
            self._audit.record(connection, user.username, datetime.now().isoformat(),
                               "AMEND_NOTE", str(original_note_id),
                               original.note_text)
        return amendment
