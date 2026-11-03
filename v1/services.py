"""Application services for PRS."""

from datetime import datetime

from database import Database
from models import Patient, VisitNote, StaffUser
from ai_categorizer import AICategorizer

EDITABLE_FIELDS = ["name", "date_of_birth", "phone", "address", "emergency_contact"]


class AuthService:
    """Logs staff in and checks permissions (FR-01, NFR-02)."""

    def __init__(self):
        self.db = Database()
        self.current_user = None
        self.failed_attempts = 0

    def login(self, username, password):
        row = self.db.get_staff(username)
        if row == None:
            self.failed_attempts = self.failed_attempts + 1
            return False
        if row[1] == password:
            self.current_user = StaffUser(row[0], row[1], row[2])
            self.failed_attempts = 0
            return True
        else:
            self.failed_attempts = self.failed_attempts + 1
            return False

    def logout(self):
        self.current_user = None

    def is_logged_in(self):
        return self.current_user != None


class PatientService:
    """Creates, retrieves and updates patient records."""

    def __init__(self, auth):
        self.db = Database()
        self.auth = auth

    def generate_patient_id(self):
        count = self.db.count_patients()
        return "P-" + str(count + 1).zfill(6)

    def register_patient(self, name, dob, phone, address, emergency_contact):
        # FR-01: reject creation when the name is missing
        if name == "" or name == None:
            print("Error: patient name is required.")
            return None
        if not self.auth.is_logged_in():
            print("Error: you must be logged in.")
            return None
        if not self.auth.current_user.canEditPatients():
            print("Error: your role cannot register patients.")
            return None

        new_id = self.generate_patient_id()
        patient = Patient(new_id, name, dob, phone, address, emergency_contact)
        self.db.insert_patient(patient)
        self.db.insert_audit(self.auth.current_user.username,
                             datetime.now().isoformat(),
                             "REGISTER_PATIENT", new_id, "")
        print("Patient registered with ID " + new_id)
        return patient

    def get_patient(self, patient_id):
        row = self.db.get_patient(patient_id)
        if row == None:
            print("No patient record found for this ID")
            return None
        p = Patient(row[0], row[1], row[2], row[3], row[4], row[5])
        return p

    def update_patient(self, patient_id, field, value):
        if not self.auth.is_logged_in():
            print("Error: you must be logged in.")
            return False
        if not self.auth.current_user.canEditPatients():
            print("Error: your role cannot update patients.")
            return False
        if field == "patient_id":
            print("Error: Patient ID cannot be changed.")
            return False
        if field not in EDITABLE_FIELDS:
            print("Error: that field cannot be edited.")
            return False
        row = self.db.get_patient(patient_id)
        if row == None:
            print("No patient record found for this ID")
            return False

        old_value = row[EDITABLE_FIELDS.index(field) + 1]
        self.db.update_patient_field(patient_id, field, value)
        self.db.insert_audit(self.auth.current_user.username,
                             datetime.now().isoformat(),
                             "UPDATE_" + field.upper(), patient_id, str(old_value))
        print("Updated " + field + " for " + patient_id)
        return True


class VisitService:
    """Adds visit notes, retrieves history, and applies amendments."""

    def __init__(self, auth):
        self.db = Database()
        self.auth = auth
        self.ai = AICategorizer()

    def add_visit_note(self, patient_id, visit_date, note_text):
        if not self.auth.is_logged_in():
            print("Error: you must be logged in.")
            return None
        if not self.auth.current_user.canAddNotes():
            print("Error: your role cannot add visit notes.")
            return None
        if note_text == "" or note_text == None:
            print("Error: note text cannot be empty.")
            return None
        if visit_date == "" or visit_date == None:
            print("Error: visit date is required.")
            return None
        row = self.db.get_patient(patient_id)
        if row == None:
            print("No patient record found for this ID")
            return None

        note = VisitNote(None, patient_id, visit_date, note_text,
                         self.auth.current_user.username)
        note_id = self.db.insert_note(note)
        self.db.insert_audit(self.auth.current_user.username,
                             datetime.now().isoformat(),
                             "ADD_NOTE", str(note_id), "")
        print("Visit note saved (note id " + str(note_id) + ").")

        category, confidence = self.ai.suggest_category(note_text)
        if category == None:
            print("No AI suggestion was available for this note.")
            return note_id

        print("Suggested category: " + category + " (confidence " + str(confidence) + ")")
        print("This is an organizational suggestion, not a diagnosis.")
        answer = input("Accept this category? (y/n): ")
        if answer.lower() == "y":
            self.db.set_note_category(note_id, category)
            self.db.insert_audit(self.auth.current_user.username,
                                 datetime.now().isoformat(),
                                 "ACCEPT_CATEGORY", str(note_id), "")
            print("Category stored.")
        else:
            print("Suggestion rejected. No category stored.")
        return note_id

    def get_visit_history(self, patient_id):
        rows = self.db.get_notes(patient_id)
        notes = []
        for row in rows:
            n = VisitNote(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
            notes.append(n)
        # FR-07: most recent first
        for i in range(len(notes)):
            for j in range(len(notes) - 1):
                if notes[j].visit_date < notes[j + 1].visit_date:
                    temp = notes[j]
                    notes[j] = notes[j + 1]
                    notes[j + 1] = temp
        return notes

    def amend_note(self, original_note_id, patient_id, visit_date, corrected_text):
        if not self.auth.is_logged_in():
            print("Error: you must be logged in.")
            return None
        note = VisitNote(None, patient_id, visit_date, corrected_text,
                         self.auth.current_user.username, None, original_note_id)
        new_id = self.db.insert_note(note)
        self.db.mark_superseded(original_note_id)
        self.db.insert_audit(self.auth.current_user.username,
                             datetime.now().isoformat(),
                             "AMEND_NOTE", str(original_note_id), "see note " + str(new_id))
        print("Amendment recorded as note " + str(new_id) + ".")
        return new_id
