"""Domain exceptions for PRS.

Services raise these instead of printing. The user interface is the only layer
that decides how an error is shown, which keeps presentation out of the
service layer.
"""


class PRSError(Exception):
    """Base class for all PRS domain errors."""


class ValidationError(PRSError):
    """Input failed a business rule (for example a missing patient name)."""


class PatientNotFoundError(PRSError):
    """No patient record exists for the given Patient ID (FR-04)."""

    def __init__(self, patient_id):
        super().__init__("No patient record found for this ID")
        self.patient_id = patient_id


class NoteNotFoundError(PRSError):
    """No visit note exists for the given note id."""


class PermissionDeniedError(PRSError):
    """The signed-in staff member's role does not allow this operation."""


class NotAuthenticatedError(PRSError):
    """No active session, or the session has expired (NFR-02)."""


class AccountLockedError(PRSError):
    """The account is locked after repeated failed sign-in attempts (NFR-02)."""


class ImmutableFieldError(PRSError):
    """An attempt was made to change a permanently fixed field (FR-02, BC-01)."""
