"""Command-line interface for the Patient Record System (PRS)."""

from services import AuthService, PatientService, VisitService

auth = AuthService()
patients = PatientService(auth)
visits = VisitService(auth)


def login_screen():
    print("\n--- PRS Login ---")
    username = input("Username: ")
    password = input("Password: ")
    if auth.login(username, password):
        print("Logged in as " + username + " (" + auth.current_user.role + ")")
        return True
    else:
        print("Login failed.")
        return False


def register_screen():
    print("\n--- Register Patient ---")
    name = input("Name: ")
    dob = input("Date of birth (YYYY-MM-DD): ")
    phone = input("Phone: ")
    address = input("Address: ")
    emergency = input("Emergency contact: ")
    patients.register_patient(name, dob, phone, address, emergency)


def search_screen():
    print("\n--- Find Patient ---")
    pid = input("Patient ID: ")
    p = patients.get_patient(pid)
    if p != None:
        print("")
        print(p)


def update_screen():
    print("\n--- Update Patient ---")
    pid = input("Patient ID: ")
    print("Editable fields: name, date_of_birth, phone, address, emergency_contact")
    field = input("Field to update: ")
    value = input("New value: ")
    patients.update_patient(pid, field, value)


def note_screen():
    print("\n--- Add Visit Note ---")
    pid = input("Patient ID: ")
    date = input("Visit date (YYYY-MM-DD): ")
    text = input("Note text: ")
    visits.add_visit_note(pid, date, text)


def history_screen():
    print("\n--- Visit History ---")
    pid = input("Patient ID: ")
    notes = visits.get_visit_history(pid)
    if len(notes) == 0:
        print("No visit notes for this patient.")
    for n in notes:
        print(n)


def amend_screen():
    print("\n--- Amend Visit Note ---")
    pid = input("Patient ID: ")
    original = input("Note id to amend: ")
    date = input("Visit date (YYYY-MM-DD): ")
    text = input("Corrected note text: ")
    visits.amend_note(original, pid, date, text)


def audit_screen():
    print("\n--- Audit Log ---")
    for row in patients.db.get_audit():
        print(row)


def menu():
    while True:
        print("\n====== Patient Record System ======")
        if auth.is_logged_in():
            print("Logged in as: " + auth.current_user.username)
        else:
            print("Not logged in")
        print("1. Login")
        print("2. Register patient")
        print("3. Find patient by ID")
        print("4. Update patient")
        print("5. Add visit note")
        print("6. View visit history")
        print("7. Amend visit note")
        print("8. View audit log")
        print("9. Logout")
        print("0. Exit")
        choice = input("Choose an option: ")
        if choice == "1":
            login_screen()
        elif choice == "2":
            register_screen()
        elif choice == "3":
            search_screen()
        elif choice == "4":
            update_screen()
        elif choice == "5":
            note_screen()
        elif choice == "6":
            history_screen()
        elif choice == "7":
            amend_screen()
        elif choice == "8":
            audit_screen()
        elif choice == "9":
            auth.logout()
            print("Logged out.")
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    menu()
