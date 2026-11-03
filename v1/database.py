"""Database access for PRS."""

import sqlite3

DB_FILE = "prs.db"


class Database:
    """Creates the schema and runs all SQL for the application."""

    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.setup()

    def setup(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT,
            name TEXT,
            date_of_birth TEXT,
            phone TEXT,
            address TEXT,
            emergency_contact TEXT,
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS visit_notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            visit_date TEXT,
            note_text TEXT,
            author TEXT,
            category TEXT,
            amends_note_id INTEGER,
            superseded INTEGER,
            recorded_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff TEXT,
            timestamp TEXT,
            action TEXT,
            target TEXT,
            previous_value TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS staff (
            username TEXT,
            password TEXT,
            role TEXT
        )""")
        c.execute("SELECT COUNT(*) FROM staff")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO staff VALUES ('frontdesk', 'pass123', 'front_desk')")
            c.execute("INSERT INTO staff VALUES ('clinician', 'pass123', 'clinician')")
            c.execute("INSERT INTO staff VALUES ('admin', 'pass123', 'admin')")
        conn.commit()
        conn.close()

    def insert_patient(self, patient):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT INTO patients VALUES (?,?,?,?,?,?,?)", patient.to_row())
        conn.commit()
        conn.close()

    def get_patient(self, patient_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE patient_id = '" + str(patient_id) + "'")
        row = c.fetchone()
        conn.close()
        return row

    def get_all_patients(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM patients")
        rows = c.fetchall()
        conn.close()
        return rows

    def update_patient_field(self, patient_id, field, value):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE patients SET " + field + " = ? WHERE patient_id = ?", (value, patient_id))
        conn.commit()
        conn.close()

    def insert_note(self, note):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT INTO visit_notes (patient_id, visit_date, note_text, author, category, amends_note_id, superseded, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                  (note.patient_id, note.visit_date, note.note_text, note.author,
                   note.category, note.amends_note_id, note.superseded, note.recordedAt))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return new_id

    def get_notes(self, patient_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM visit_notes WHERE patient_id = ?", (patient_id,))
        rows = c.fetchall()
        conn.close()
        return rows

    def set_note_category(self, note_id, category):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE visit_notes SET category = ? WHERE note_id = ?", (category, note_id))
        conn.commit()
        conn.close()

    def mark_superseded(self, note_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE visit_notes SET superseded = 1 WHERE note_id = ?", (note_id,))
        conn.commit()
        conn.close()

    def insert_audit(self, staff, timestamp, action, target, previous_value):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT INTO audit_log (staff, timestamp, action, target, previous_value) VALUES (?,?,?,?,?)",
                  (staff, timestamp, action, target, previous_value))
        conn.commit()
        conn.close()

    def get_audit(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM audit_log")
        rows = c.fetchall()
        conn.close()
        return rows

    def get_staff(self, username):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM staff WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
        return row

    def count_patients(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM patients")
        n = c.fetchone()[0]
        conn.close()
        return n
