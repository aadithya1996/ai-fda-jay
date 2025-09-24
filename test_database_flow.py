from database import (
    initialize_database,
    add_patient,
    book_appointment,
)
from dotenv import load_dotenv

# Load environment variables for the test script
load_dotenv()

def run_test_flow():
    """
    An interactive command-line tool to test the patient and appointment database functions.
    """
    print("--- Starting Database Test Flow ---")
    db_connection = initialize_database()
    
    if not db_connection:
        print("Database initialization failed. Exiting.")
        return

    # --- Step 1: Add a new patient ---
    print("\nStep 1: Add a New Patient")
    print("-------------------------")
    name = input("Enter Patient Name: ")
    phone = input("Enter Phone Number: ")
    email = input("Enter Email Address: ")
    illness = input("Enter Illness: ")
    insurance = input("Enter Insurance Provider: ")

    patient_result = add_patient(db_connection, name, phone, email, illness, insurance)
    print(f"\nResult: {patient_result}\n")

    if patient_result.get("status") in ["created", "exists"]:
        patient_id = patient_result.get("patient_id")
        print(f"Successfully retrieved Patient ID: {patient_id}")
        
        # --- Step 2: Book an appointment ---
        print("\nStep 2: Book an Appointment")
        print("---------------------------")
        print("Enter appointment details for the patient above.")
        date = input("Enter Date (YYYY-MM-DD): ")
        time = input("Enter Time (HH:MM): ")
        
        # We use the same illness as provided during intake for this test.
        appointment_result = book_appointment(db_connection, patient_id, date, time, illness)
        print(f"\nResult: {appointment_result}\n")

        if appointment_result.get("status") == "success":
            print("--- Test Flow Completed Successfully ---")
            print("An appointment should now exist in your database.")
        else:
            print("--- Test Flow Failed at Appointment Booking ---")
    else:
        print("--- Test Flow Failed at Patient Creation ---")

    db_connection.close()
    print("\nDatabase connection closed.")

if __name__ == "__main__":
    run_test_flow() 