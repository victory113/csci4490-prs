"""Domain models for the Patient Record System (PRS)."""

from datetime import datetime


class Patient:
    """A patient record."""

    def __init__(self, patient_id, name, date_of_birth, phone, address, emergency_contact):
        self.patient_id = patient_id
        self.name = name
        self.date_of_birth = date_of_birth
        self.phone = phone
        self.address = address
        self.emergency_contact = emergency_contact
        self.createdAt = datetime.now().isoformat()

    def to_row(self):
        return (self.patient_id, self.name, self.date_of_birth, self.phone,
                self.address, self.emergency_contact, self.createdAt)

    def __str__(self):
        return ("Patient ID: " + str(self.patient_id) + "\n"
                + "Name: " + str(self.name) + "\n"
                + "Date of Birth: " + str(self.date_of_birth) + "\n"
                + "Phone: " + str(self.phone) + "\n"
                + "Address: " + str(self.address) + "\n"
                + "Emergency Contact: " + str(self.emergency_contact))


class VisitNote:
    """A dated note attached to a patient record."""

    def __init__(self, note_id, patient_id, visit_date, note_text, author,
                 category=None, amends_note_id=None, superseded=0):
        self.note_id = note_id
        self.patient_id = patient_id
        self.visit_date = visit_date
        self.note_text = note_text
        self.author = author
        self.category = category
        self.amends_note_id = amends_note_id
        self.superseded = superseded
        self.recordedAt = datetime.now().isoformat()

    def __str__(self):
        line = "[" + str(self.visit_date) + "] " + str(self.note_text)
        if self.category:
            line = line + "  (category: " + str(self.category) + ")"
        if self.superseded:
            line = line + "  *** SUPERSEDED ***"
        return line


class StaffUser:
    """A staff member who can log in to PRS."""

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role

    def canEditPatients(self):
        if self.role == "front_desk" or self.role == "admin":
            return True
        return False

    def canAddNotes(self):
        if self.role == "clinician" or self.role == "admin":
            return True
        return False
