"""Domain models for the Patient Record System (PRS).

The Patient ID is enforced as immutable here at the object level (FR-02,
BC-01). Uniqueness is a separate concern enforced by the database schema in
database.py, and encapsulation is a third concern handled by keeping state
behind properties.
"""

from datetime import datetime

from errors import ImmutableFieldError, ValidationError

EDITABLE_PATIENT_FIELDS = ("name", "date_of_birth", "phone", "address", "emergency_contact")

VALID_ROLES = ("front_desk", "clinician", "admin")

ROLE_PERMISSIONS = {
    "front_desk": frozenset({"register_patient", "update_patient", "view_patient"}),
    "clinician": frozenset({"view_patient", "add_note", "amend_note", "confirm_category"}),
    "admin": frozenset({"register_patient", "update_patient", "view_patient",
                        "add_note", "amend_note", "confirm_category", "view_audit"}),
}


class Patient:
    """A patient record whose Patient ID can never change after construction."""

    __slots__ = ("_patient_id", "_name", "_date_of_birth", "_phone",
                 "_address", "_emergency_contact", "_created_at")

    def __init__(self, patient_id, name, date_of_birth="", phone="",
                 address="", emergency_contact="", created_at=None):
        if not patient_id:
            raise ValidationError("A Patient ID is required.")
        if not name or not name.strip():
            raise ValidationError("Patient name is required.")
        object.__setattr__(self, "_patient_id", patient_id)
        self._name = name.strip()
        self._date_of_birth = date_of_birth
        self._phone = phone
        self._address = address
        self._emergency_contact = emergency_contact
        self._created_at = created_at or datetime.now().isoformat()

    # --- Patient ID: read-only, with no setter ---------------------------
    @property
    def patient_id(self):
        """The permanent Patient ID. There is deliberately no setter."""
        return self._patient_id

    def __setattr__(self, attribute, value):
        """Block reassignment of the Patient ID through any attribute path."""
        if attribute in ("patient_id", "_patient_id"):
            raise ImmutableFieldError(
                "Patient ID cannot be changed once the record exists.")
        object.__setattr__(self, attribute, value)

    # --- Editable, validated fields --------------------------------------
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value or not value.strip():
            raise ValidationError("Patient name cannot be empty.")
        self._name = value.strip()

    @property
    def date_of_birth(self):
        return self._date_of_birth

    @date_of_birth.setter
    def date_of_birth(self, value):
        self._date_of_birth = value

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, value):
        self._phone = value

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value

    @property
    def emergency_contact(self):
        return self._emergency_contact

    @emergency_contact.setter
    def emergency_contact(self, value):
        self._emergency_contact = value

    @property
    def created_at(self):
        return self._created_at

    def as_dict(self):
        return {
            "patient_id": self._patient_id,
            "name": self._name,
            "date_of_birth": self._date_of_birth,
            "phone": self._phone,
            "address": self._address,
            "emergency_contact": self._emergency_contact,
            "created_at": self._created_at,
        }

    def __repr__(self):
        return f"Patient({self._patient_id!r}, {self._name!r})"


class VisitNote:
    """A dated note belonging to exactly one patient record (BC-02)."""

    def __init__(self, note_id, patient_id, visit_date, note_text, author,
                 category=None, amends_note_id=None, superseded=False,
                 recorded_at=None):
        if not note_text or not note_text.strip():
            raise ValidationError("Visit note text cannot be empty.")
        if not visit_date:
            raise ValidationError("A visit date is required.")
        self.note_id = note_id
        self.patient_id = patient_id
        self.visit_date = visit_date
        self.note_text = note_text.strip()
        self.author = author
        self.category = category
        self.amends_note_id = amends_note_id
        self.superseded = bool(superseded)
        self.recorded_at = recorded_at or datetime.now().isoformat()

    def __repr__(self):
        return f"VisitNote({self.note_id!r}, {self.patient_id!r}, {self.visit_date!r})"


class StaffUser:
    """A staff member, whose permissions derive from their role."""

    def __init__(self, username, role):
        if role not in VALID_ROLES:
            raise ValidationError(f"Unknown role: {role}")
        self.username = username
        self.role = role

    def has_permission(self, action):
        return action in ROLE_PERMISSIONS[self.role]

    def __repr__(self):
        return f"StaffUser({self.username!r}, {self.role!r})"
