"""Repositories: the only place that knows SQL.

These realise the IPatientRepository and IVisitRepository interfaces from the
Assignment #3 logical view. Services depend on a repository object that is
passed in, so a service can be exercised against a different repository
without changing the service.

Every statement uses bound parameters. No SQL is built by string
concatenation.
"""

from models import Patient, VisitNote, StaffUser, EDITABLE_PATIENT_FIELDS


class PatientRepository:
    """Reads and writes patient records (realises IPatientRepository)."""

    def __init__(self, database):
        self._db = database

    def next_patient_id(self, connection):
        """Allocate the next Patient ID from a counter that only increases.

        The counter is never decremented and is read and written inside the
        caller's transaction, so an ID is never reused even after a record is
        removed (BC-01).
        """
        connection.execute(
            "UPDATE counters SET value = value + 1 WHERE name = 'patient_id'")
        row = connection.execute(
            "SELECT value FROM counters WHERE name = 'patient_id'").fetchone()
        return f"P-{row['value']:06d}"

    def insert(self, connection, patient):
        connection.execute(
            "INSERT INTO patients (patient_id, name, date_of_birth, phone,"
            " address, emergency_contact, created_at) VALUES (?,?,?,?,?,?,?)",
            (patient.patient_id, patient.name, patient.date_of_birth,
             patient.phone, patient.address, patient.emergency_contact,
             patient.created_at))

    def find_by_id(self, patient_id):
        row = self._db.connection.execute(
            "SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
        if row is None:
            return None
        return Patient(row["patient_id"], row["name"], row["date_of_birth"],
                       row["phone"], row["address"], row["emergency_contact"],
                       row["created_at"])

    def update_field(self, connection, patient_id, field, value):
        if field not in EDITABLE_PATIENT_FIELDS:
            raise ValueError(f"Field not editable: {field}")
        # The field name is validated against a fixed allow-list before being
        # placed in the statement; the value is always bound.
        connection.execute(
            f"UPDATE patients SET {field} = ? WHERE patient_id = ?",
            (value, patient_id))

    def exists(self, patient_id):
        row = self._db.connection.execute(
            "SELECT 1 FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
        return row is not None


class VisitRepository:
    """Reads and writes visit notes (realises IVisitRepository)."""

    def __init__(self, database):
        self._db = database

    def insert(self, connection, note):
        cursor = connection.execute(
            "INSERT INTO visit_notes (patient_id, visit_date, note_text, author,"
            " category, amends_note_id, superseded, recorded_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (note.patient_id, note.visit_date, note.note_text, note.author,
             note.category, note.amends_note_id, int(note.superseded),
             note.recorded_at))
        return cursor.lastrowid

    def find_by_patient(self, patient_id):
        """Return notes most recent first, ordered by the database (FR-07)."""
        rows = self._db.connection.execute(
            "SELECT * FROM visit_notes WHERE patient_id = ?"
            " ORDER BY visit_date DESC, note_id DESC", (patient_id,)).fetchall()
        return [VisitNote(r["note_id"], r["patient_id"], r["visit_date"],
                          r["note_text"], r["author"], r["category"],
                          r["amends_note_id"], r["superseded"], r["recorded_at"])
                for r in rows]

    def find_by_id(self, note_id):
        row = self._db.connection.execute(
            "SELECT * FROM visit_notes WHERE note_id = ?", (note_id,)).fetchone()
        if row is None:
            return None
        return VisitNote(row["note_id"], row["patient_id"], row["visit_date"],
                         row["note_text"], row["author"], row["category"],
                         row["amends_note_id"], row["superseded"], row["recorded_at"])

    def set_category(self, connection, note_id, category):
        connection.execute("UPDATE visit_notes SET category = ? WHERE note_id = ?",
                           (category, note_id))

    def mark_superseded(self, connection, note_id):
        connection.execute("UPDATE visit_notes SET superseded = 1 WHERE note_id = ?",
                           (note_id,))


class AuditRepository:
    """Append-only audit trail (FR-10, NFR-04)."""

    def __init__(self, database):
        self._db = database

    def record(self, connection, staff, timestamp, action, target, previous_value=""):
        connection.execute(
            "INSERT INTO audit_log (staff, timestamp, action, target, previous_value)"
            " VALUES (?,?,?,?,?)", (staff, timestamp, action, target, previous_value))

    def all_entries(self):
        return self._db.connection.execute(
            "SELECT * FROM audit_log ORDER BY entry_id").fetchall()


class StaffRepository:
    """Staff accounts and sign-in state."""

    def __init__(self, database):
        self._db = database

    def find(self, username):
        return self._db.connection.execute(
            "SELECT * FROM staff WHERE username = ?", (username,)).fetchone()

    def to_user(self, row):
        return StaffUser(row["username"], row["role"])

    def record_failure(self, username, attempts, locked):
        with self._db.transaction() as connection:
            connection.execute(
                "UPDATE staff SET failed_attempts = ?, locked = ? WHERE username = ?",
                (attempts, int(locked), username))

    def reset_failures(self, username):
        with self._db.transaction() as connection:
            connection.execute(
                "UPDATE staff SET failed_attempts = 0 WHERE username = ?", (username,))
