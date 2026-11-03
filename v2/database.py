"""Database connection and schema for PRS.

One connection is opened for the life of the application instead of one per
query, and related writes are committed together through the transaction()
context manager so a visit note and its audit entry cannot be separated.
"""

import hashlib
import os
import sqlite3
from contextlib import contextmanager

DEFAULT_DB_FILE = "prs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id        TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    date_of_birth     TEXT,
    phone             TEXT,
    address           TEXT,
    emergency_contact TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visit_notes (
    note_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     TEXT NOT NULL REFERENCES patients(patient_id),
    visit_date     TEXT NOT NULL,
    note_text      TEXT NOT NULL,
    author         TEXT NOT NULL,
    category       TEXT,
    amends_note_id INTEGER REFERENCES visit_notes(note_id),
    superseded     INTEGER NOT NULL DEFAULT 0,
    recorded_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_patient_date
    ON visit_notes (patient_id, visit_date DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    entry_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    staff          TEXT NOT NULL,
    timestamp      TEXT NOT NULL,
    action         TEXT NOT NULL,
    target         TEXT NOT NULL,
    previous_value TEXT
);

CREATE TABLE IF NOT EXISTS staff (
    username        TEXT PRIMARY KEY,
    password_salt   TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS counters (
    name  TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
"""

SEED_STAFF = (
    ("frontdesk", "pass123", "front_desk"),
    ("clinician", "pass123", "clinician"),
    ("admin", "pass123", "admin"),
)


def hash_password(password, salt=None):
    """Derive a salted hash. Plaintext passwords are never stored (NFR-02)."""
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), 100_000)
    return salt, digest.hex()


class Database:
    """Owns the single sqlite3 connection and creates the schema."""

    def __init__(self, db_file=DEFAULT_DB_FILE):
        self.db_file = db_file
        self._connection = sqlite3.connect(db_file)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._seed()

    @property
    def connection(self):
        return self._connection

    def _create_schema(self):
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    def _seed(self):
        cursor = self._connection.execute("SELECT COUNT(*) FROM staff")
        if cursor.fetchone()[0] == 0:
            for username, password, role in SEED_STAFF:
                salt, digest = hash_password(password)
                self._connection.execute(
                    "INSERT INTO staff (username, password_salt, password_hash, role)"
                    " VALUES (?, ?, ?, ?)", (username, salt, digest, role))
        cursor = self._connection.execute(
            "SELECT COUNT(*) FROM counters WHERE name = 'patient_id'")
        if cursor.fetchone()[0] == 0:
            self._connection.execute(
                "INSERT INTO counters (name, value) VALUES ('patient_id', 0)")
        self._connection.commit()

    @contextmanager
    def transaction(self):
        """Commit every statement in the block together, or none of them."""
        try:
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def close(self):
        self._connection.close()
