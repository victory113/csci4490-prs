"""Command-line interface for PRS (prs.ui).

This module is the only one that prints or reads input. It catches domain
errors raised by the services and decides how to present them.
"""

from ai_categorizer import AICategorizer
from database import Database
from errors import PRSError
from repositories import (AuditRepository, PatientRepository, StaffRepository,
                          VisitRepository)
from services import AuthService, PatientService, VisitService


def build_application(db_file="prs.db"):
    """Compose the object graph: repositories and services are wired here."""
    database = Database(db_file)
    patients_repo = PatientRepository(database)
    visits_repo = VisitRepository(database)
    audit_repo = AuditRepository(database)
    staff_repo = StaffRepository(database)

    auth = AuthService(staff_repo)
    patient_service = PatientService(database, patients_repo, audit_repo, auth)
    visit_service = VisitService(database, visits_repo, patients_repo, audit_repo,
                                 auth, AICategorizer())
    return database, auth, patient_service, visit_service, audit_repo


class PRSConsole:
    def __init__(self):
        (self.database, self.auth, self.patients,
         self.visits, self.audit) = build_application()

    # --- individual screens ----------------------------------------------
    def login(self):
        print("\n--- Sign in ---")
        username = input("Username: ")
        password = input("Password: ")
        user = self.auth.login(username, password)
        print(f"Signed in as {user.username} ({user.role})")

    def register_patient(self):
        print("\n--- Register Patient ---")
        patient = self.patients.register_patient(
            input("Name: "),
            input("Date of birth (YYYY-MM-DD): "),
            input("Phone: "),
            input("Address: "),
            input("Emergency contact: "))
        print(f"Patient registered with ID {patient.patient_id}")

    def find_patient(self):
        print("\n--- Find Patient ---")
        patient = self.patients.get_patient(input("Patient ID: "))
        print()
        for key, value in patient.as_dict().items():
            print(f"{key.replace('_', ' ').title():>18}: {value}")

    def update_patient(self):
        print("\n--- Update Patient ---")
        patient_id = input("Patient ID: ")
        print("Editable fields: name, date_of_birth, phone, address, emergency_contact")
        field = input("Field to update: ")
        value = input("New value: ")
        self.patients.update_patient(patient_id, field, value)
        print(f"Updated {field} for {patient_id}")

    def add_note(self):
        print("\n--- Add Visit Note ---")
        patient_id = input("Patient ID: ")
        visit_date = input("Visit date (YYYY-MM-DD): ")
        note_text = input("Note text: ")

        note = self.visits.add_visit_note(patient_id, visit_date, note_text)
        print(f"Visit note saved (note id {note.note_id}).")

        suggestion = self.visits.request_category_suggestion(note_text)
        if not suggestion.available:
            self.visits.record_no_suggestion(note.note_id, suggestion.reason)
            print(f"No AI suggestion was available ({suggestion.reason}).")
            print("The note is saved without a category.")
            return

        print(f"\nSuggested category: {suggestion.category} "
              f"(confidence {suggestion.confidence}, source: {suggestion.source})")
        print("This is an organizational suggestion, not a diagnosis.")
        if input("Accept this category? (y/n): ").strip().lower() == "y":
            self.visits.confirm_category(note.note_id, suggestion.category)
            print("Category stored.")
        else:
            print("Suggestion rejected. No category stored.")

    def visit_history(self):
        print("\n--- Visit History ---")
        notes = self.visits.get_visit_history(input("Patient ID: "))
        if not notes:
            print("No visit notes for this patient.")
            return
        for note in notes:
            line = f"[{note.visit_date}] {note.note_text}"
            if note.category:
                line += f"  (category: {note.category})"
            if note.amends_note_id:
                line += f"  (amends note {note.amends_note_id})"
            if note.superseded:
                line += "  *** SUPERSEDED ***"
            print(line)

    def amend_note(self):
        print("\n--- Amend Visit Note ---")
        note_id = input("Note id to amend: ")
        visit_date = input("Visit date (YYYY-MM-DD): ")
        corrected = input("Corrected note text: ")
        amendment = self.visits.amend_note(int(note_id), visit_date, corrected)
        print(f"Amendment recorded as note {amendment.note_id}. "
              "The original is retained and marked superseded.")

    def view_audit(self):
        print("\n--- Audit Log ---")
        self.auth.require_user("view_audit")
        for row in self.audit.all_entries():
            print(f"{row['entry_id']:>3}  {row['timestamp']}  {row['staff']:<10} "
                  f"{row['action']:<18} {row['target']:<10} {row['previous_value'] or ''}")

    def immutability_demo(self):
        """Demonstrate what happens when the Patient ID is changed (Part 2.2)."""
        print("\n--- Patient ID Immutability Check ---")
        patient = self.patients.get_patient(input("Patient ID: "))
        print(f"Current Patient ID: {patient.patient_id}")
        print("\nAttempt 1 - direct attribute assignment: patient.patient_id = 'P-999999'")
        try:
            patient.patient_id = "P-999999"
            print("  FAILED: the ID was changed.")
        except Exception as exc:
            print(f"  Blocked -> {type(exc).__name__}: {exc}")
        print("\nAttempt 2 - private attribute: patient._patient_id = 'P-999999'")
        try:
            patient._patient_id = "P-999999"
            print("  FAILED: the ID was changed.")
        except Exception as exc:
            print(f"  Blocked -> {type(exc).__name__}: {exc}")
        print("\nAttempt 3 - through the service: update_patient(..., 'patient_id', ...)")
        try:
            self.patients.update_patient(patient.patient_id, "patient_id", "P-999999")
            print("  FAILED: the ID was changed.")
        except Exception as exc:
            print(f"  Blocked -> {type(exc).__name__}: {exc}")
        print(f"\nPatient ID is still: {patient.patient_id}")

    # --- menu -------------------------------------------------------------
    MENU = (
        ("1", "Sign in", "login"),
        ("2", "Register patient", "register_patient"),
        ("3", "Find patient by ID", "find_patient"),
        ("4", "Update patient", "update_patient"),
        ("5", "Add visit note", "add_note"),
        ("6", "View visit history", "visit_history"),
        ("7", "Amend visit note", "amend_note"),
        ("8", "View audit log", "view_audit"),
        ("9", "Patient ID immutability check", "immutability_demo"),
        ("L", "Sign out", None),
        ("0", "Exit", None),
    )

    def run(self):
        while True:
            user = self.auth.current_user
            print("\n====== Patient Record System ======")
            print(f"Signed in as: {user.username} ({user.role})" if user else "Not signed in")
            for key, label, _ in self.MENU:
                print(f"{key}. {label}")
            choice = input("Choose an option: ").strip().upper()

            if choice == "0":
                print("Goodbye.")
                self.database.close()
                return
            if choice == "L":
                self.auth.logout()
                print("Signed out.")
                continue

            handler = next((name for key, _, name in self.MENU if key == choice), None)
            if handler is None:
                print("Invalid option.")
                continue
            try:
                getattr(self, handler)()
            except PRSError as exc:
                print(f"\n{exc}")
            except ValueError:
                print("\nThat value was not in the expected format.")


if __name__ == "__main__":
    PRSConsole().run()
