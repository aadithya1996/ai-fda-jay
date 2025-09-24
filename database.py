import sqlite3
from thefuzz import process
from datetime import datetime, timedelta
import pytz
import re
from email_notifications import send_appointment_confirmation

# Define the clinic's timezone
TIMEZONE = pytz.timezone('America/New_York')

def _correct_and_validate_email(email):
    """
    Tries to correct common email typos and validates the format.
    Returns (corrected_email, is_valid, message).
    """
    # Attempt to correct a common typo: space instead of '@'
    corrected_email = email.strip()
    if '@' not in corrected_email and ' ' in corrected_email:
        parts = corrected_email.rsplit(' ', 1)
        # Check if the part after the space looks like a domain
        if '.' in parts[1]:
            corrected_email = '@'.join(parts)
            print(f"Corrected potential email typo: '{email}' -> '{corrected_email}'")

    # Basic regex for email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_regex, corrected_email):
        return corrected_email, True, "Email is valid."
    else:
        # Return the original email in the error message
        return email, False, f"The provided email '{email}' is not in a valid format. Please provide a valid email address (e.g., name@example.com)."

def is_valid_appointment_datetime(appointment_date, appointment_time):
    """
    Validates the appointment date and time against clinic rules.
    - Must be in the future.
    - Must not be on a weekend.
    - Must be on the hour or half-hour.
    - Must be within clinic hours (8:00 AM to 4:30 PM).
    """
    try:
        # Combine date and time and make it timezone-aware
        start_time_full = datetime.strptime(f"{appointment_date} {appointment_time}", '%Y-%m-%d %H:%M')
        localized_start_time = TIMEZONE.localize(start_time_full)
        
        # 1. Check if the appointment is in the past
        if localized_start_time < datetime.now(TIMEZONE):
            return False, "Appointments cannot be booked in the past. Please provide a future date and time."

        # 2. Check if the appointment is on a weekend (Monday=0, Sunday=6)
        if localized_start_time.weekday() in [5, 6]:
            return False, "The clinic is closed on Saturdays and Sundays. Please choose a weekday."
            
        # 3. Check if the appointment is on the hour or half-hour
        if localized_start_time.minute not in [0, 30]:
            return False, "Appointments must be scheduled on the hour or half-hour (e.g., 9:00, 9:30)."

        # 4. Check if the appointment is within clinic hours (8:00 AM to 4:30 PM)
        time_obj = localized_start_time.time()
        if not (datetime.strptime('08:00', '%H:%M').time() <= time_obj < datetime.strptime('17:00', '%H:%M').time()):
            return False, "Appointments can only be booked between 8:00 AM and 4:30 PM EST."

        return True, "valid"
        
    except ValueError:
        return False, "Invalid time or date format. Please use HH:MM for time and YYYY-MM-DD for date."

def populate_insurance_data(con):
    """
    Populates the Insurance table with the provided data.
    """
    cur = con.cursor()
    insurance_data = [
        (1, 'Aetna', 1, 'Cardiology, Diabetes, Cancer, Orthopedics, Pediatrics'),
        (2, 'Blue Cross Blue Shield', 1, 'General, Heart Disease, Mental Health, Orthopedics, Respiratory Disorders'),
        (3, 'UnitedHealthcare', 1, 'Diabetes, Hypertension, Cardiology, Maternity, Pediatrics'),
        (4, 'Cigna', 1, 'Oncology, Cardiology, Dermatology, Gastroenterology'),
        (5, 'Humana', 0, 'Diabetes, Cancer, Kidney Disorders, Vision & Dental'),
        (6, 'Kaiser Permanente', 1, 'Pediatrics, Cardiology, Diabetes, Preventive Care'),
        (7, 'Allianz Care', 1, 'Global Health, Critical Illness, Mental Health, Maternity'),
        (8, 'Prudential Health', 1, 'Cancer, Diabetes, Cardiology, Orthopedics, Chronic Illness'),
        (9, 'Manulife', 1, 'Diabetes, Heart Disease, Stroke, Cancer, General Care'),
        (10, 'ICICI Lombard (India)', 1, 'Cancer, Diabetes, Cardiology, COVID-19, Critical Illness'),
        (11, 'HDFC ERGO Health (India)', 1, 'Orthopedics, Maternity, Cancer, Diabetes, Neurology'),
        (12, 'Star Health (India)', 1, 'Pediatrics, Diabetes, Heart Disease, Cancer, Maternity'),
        (13, 'Max Bupa (Niva Bupa, India)', 1, 'Cancer, Diabetes, Cardiology, Pediatrics, Respiratory Disorders'),
        (14, 'Religare Care (Care Health)', 1, 'Diabetes, Cancer, Stroke, Heart Disease, Critical Illness'),
        (15, 'New India Assurance', 1, 'General, Cancer, Diabetes, Heart Disease, Neurological Disorders')
    ]
    cur.executemany("INSERT INTO Insurance VALUES (?, ?, ?, ?)", insurance_data)
    con.commit()
    print("Insurance table populated with 15 records.")

def find_existing_patient(con, patient_name, phone_number):
    """
    Finds an existing patient by phone number and fuzzy name matching.
    Returns PatientId if a match is found, otherwise None.
    """
    cur = con.cursor()
    cur.execute("SELECT PatientId, PatientName FROM Patients WHERE PatientPhoneNumber = ?", (phone_number,))
    potential_matches = cur.fetchall()

    if not potential_matches:
        return None

    # Use fuzzy matching on the name for all patients with the same phone number
    names = [match[1] for match in potential_matches]
    best_match, score = process.extractOne(patient_name, names)

    if score >= 85: # Using a higher threshold for matching existing patients
        # Get the ID of the best match
        for match in potential_matches:
            if match[1] == best_match:
                return match[0]
    
    return None

def find_existing_patient_by_email(con, patient_email):
    """
    Finds an existing patient by their unique email address.
    Returns PatientId if a match is found, otherwise None.
    """
    cur = con.cursor()
    cur.execute("SELECT PatientId FROM Patients WHERE PatientEmail = ?", (patient_email,))
    result = cur.fetchone()
    return result[0] if result else None

def add_patient(con, patient_name, phone_number, patient_email, illness, insurance_name):
    """
    Adds a new patient to the database if they do not already exist based on email.
    """
    # 0. Validate and correct the email before proceeding
    patient_email, is_valid, message = _correct_and_validate_email(patient_email)
    if not is_valid:
        return {"status": "error", "message": message}

    # First, check if a patient with this email already exists
    existing_patient_id = find_existing_patient_by_email(con, patient_email)
    if existing_patient_id:
        print(f"Patient with email '{patient_email}' already exists with ID {existing_patient_id}.")
        return {"status": "exists", "patient_id": existing_patient_id}

    # Find the insurance ID using fuzzy matching
    cur = con.cursor()
    cur.execute("SELECT InsuranceName FROM Insurance")
    all_insurance_names = [row[0] for row in cur.fetchall()]
    best_match, score = process.extractOne(insurance_name, all_insurance_names)
    
    insurance_id = None
    if score >= 80:
        cur.execute("SELECT InsuranceId FROM Insurance WHERE InsuranceName = ?", (best_match,))
        result = cur.fetchone()
        if result:
            insurance_id = result[0]

    # Insert the new patient record
    try:
        cur.execute(
            "INSERT INTO Patients (PatientName, PatientPhoneNumber, PatientEmail, PatientIllness, InsuranceId) VALUES (?, ?, ?, ?, ?)",
            (patient_name, phone_number, patient_email, illness, insurance_id)
        )
        con.commit()
        new_patient_id = cur.lastrowid
        print(f"Successfully added new patient '{patient_name}' with ID {new_patient_id}.")
        return {"status": "created", "patient_id": new_patient_id}
    except sqlite3.IntegrityError:
        # This will catch violations of the UNIQUE constraint on PatientEmail
        return {"status": "error", "message": f"A patient with the email '{patient_email}' already exists."}
    except sqlite3.Error as e:
        print(f"Database insert error: {e}")
        return {"status": "error", "message": "Failed to add new patient."}

def get_patient_details(con, patient_name, patient_email):
    """
    Finds a patient by email and returns their non-sensitive details.
    """
    # 0. Validate the email before querying
    patient_email, is_valid, message = _correct_and_validate_email(patient_email)
    if not is_valid:
        return {"status": "error", "message": message}

    patient_id = find_existing_patient_by_email(con, patient_email)
    
    if not patient_id:
        return {
            "status": "not_found",
            "message": "No patient record was found with these details. You can proceed with creating a new record if needed."
        }
    
    try:
        cur = con.cursor()
        cur.execute("SELECT PatientName FROM Patients WHERE PatientId = ?", (patient_id,))
        result = cur.fetchone()
        
        if not result:
            # This is unlikely if find_existing_patient worked, but good for safety
            return {"status": "error", "message": "Found patient ID but could not retrieve details."}
            
        return {
            "status": "found",
            "patient_id": patient_id,
            "patient_name": result[0],
            "message": f"Patient record found for {result[0]}."
        }

    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        return {"status": "error", "message": "There was an error checking for the patient."}

def check_availability(con, appointment_date, appointment_time, illness):
    """
    Checks if a specific time slot is available with the appropriate doctor.
    """
    # 0. Validate the date and time first
    is_valid, message = is_valid_appointment_datetime(appointment_date, appointment_time)
    if not is_valid:
        return {"status": "error", "message": message}

    # 1. Assign doctor based on illness
    illness_lower = illness.lower()
    if 'acl' in illness_lower or 'joint pain' in illness_lower:
        doctor_name = 'Dr. Jonas'
    else:
        doctor_name = 'Dr. Katherine'

    # 2. Format the time string for querying
    try:
        start_time_full = datetime.strptime(f"{appointment_date} {appointment_time}", '%Y-%m-%d %H:%M')
        start_time_str = start_time_full.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # This is a fallback, should not be reached if validation is correct
        return {"status": "error", "message": "Invalid time or date format."}

    # 3. Check for an existing appointment
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT AppointmentId FROM Appointments WHERE DoctorName = ? AND AppointmentTimeStart = ?",
            (doctor_name, start_time_str)
        )
        if cur.fetchone():
            return {"status": "unavailable", "doctor_name": doctor_name, "message": f"The slot at {appointment_time} with {doctor_name} is already booked."}
        else:
            return {"status": "available", "doctor_name": doctor_name, "message": f"The slot at {appointment_time} with {doctor_name} is available."}
    except sqlite3.Error as e:
        print(f"Database availability check error: {e}")
        return {"status": "error", "message": "A database error occurred while checking availability."}

def cancel_appointment(con, patient_id, appointment_date, appointment_time):
    """
    Cancels an existing appointment for a given patient at a specific time.
    """

    try:
        start_time_full = datetime.strptime(f"{appointment_date} {appointment_time}", '%Y-%m-%d %H:%M')
        start_time_str = start_time_full.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return {"status": "error", "message": "Invalid time or date format."}
    
    try:
        cur = con.cursor()
        # First, find the appointment to ensure it exists and belongs to the patient
        cur.execute(
            "SELECT AppointmentId FROM Appointments WHERE PatientId = ? AND AppointmentTimeStart = ?",
            (patient_id, start_time_str)
        )
        appointment = cur.fetchone()

        if not appointment:
            return {"status": "not_found", "message": "No matching appointment was found for this patient at the specified time."}

        # Delete the appointment
        cur.execute("DELETE FROM Appointments WHERE AppointmentId = ?", (appointment[0],))
        con.commit()
        
        if cur.rowcount > 0:
            print(f"Successfully canceled appointment {appointment[0]} for patient {patient_id}.")
            return {"status": "success", "message": "The appointment has been successfully canceled."}
        else:
            # This case is unlikely if the appointment was found, but it's good practice
            return {"status": "error", "message": "Failed to cancel the appointment. Please try again."}
            
    except sqlite3.Error as e:
        print(f"Database cancellation error: {e}")
        return {"status": "error", "message": "A database error occurred during cancellation."}

def update_patient(con, patient_id, new_phone_number=None, new_insurance_name=None, new_patient_email=None):
    """
    Updates a patient's record. This can include phone number, insurance, or email.
    """
    if not any([new_phone_number, new_insurance_name, new_patient_email]):
        return {"status": "error", "message": "No update information was provided."}

    updates = []
    params = []

    # Validate and prepare the email update if provided.
    if new_patient_email:
        corrected_email, is_valid, message = _correct_and_validate_email(new_patient_email)
        if not is_valid:
            return {"status": "validation_error", "message": message}
        updates.append("PatientEmail = ?")
        params.append(corrected_email)

    # Prepare the phone number update if provided.
    if new_phone_number:
        updates.append("PatientPhoneNumber = ?")
        params.append(new_phone_number)

    try:
        cur = con.cursor()

        # Prepare the insurance update if provided (requires a DB lookup).
        if new_insurance_name:
            cur.execute("SELECT InsuranceName FROM Insurance")
            all_insurance_names = [row[0] for row in cur.fetchall()]
            best_match, score = process.extractOne(new_insurance_name, all_insurance_names)
            
            if score >= 80:
                cur.execute("SELECT InsuranceId FROM Insurance WHERE InsuranceName = ?", (best_match,))
                result = cur.fetchone()
                if result:
                    updates.append("InsuranceId = ?")
                    params.append(result[0])
            else:
                # If the insurance name is not found, return an error instead of proceeding.
                return {"status": "validation_error", "message": f"The insurance provider '{new_insurance_name}' was not found in our system."}

        if not updates:
            return {"status": "error", "message": "No valid update information could be processed."}

        # Build and execute the final UPDATE statement.
        update_query = f"UPDATE Patients SET {', '.join(updates)} WHERE PatientId = ?"
        params.append(patient_id)
        
        cur.execute(update_query, tuple(params))
        con.commit()

        if cur.rowcount > 0:
            print(f"Successfully updated record for patient ID {patient_id}.")
            return {"status": "success", "message": "Patient information has been updated."}
        else:
            return {"status": "not_found", "message": "No patient record was found with the given ID."}

    except sqlite3.Error as e:
        print(f"Database update error: {e}")
        return {"status": "error", "message": "A database error occurred during the update."}

def book_appointment(con, patient_id, appointment_date, appointment_time, illness):
    """
    Books an appointment for a patient, handling all validation and conflict checking.
    This function is a single, atomic operation for booking.
    """
    # Step 1: Centralized, strict validation of the requested date and time.
    is_valid, message = is_valid_appointment_datetime(appointment_date, appointment_time)
    if not is_valid:
        print(f"SYSTEM_VALIDATION_ERROR: {message}")
        return {"status": "validation_error", "message": message}

    # Step 2: Assign the correct doctor based on the patient's illness.
    illness_lower = illness.lower()
    if 'acl' in illness_lower or 'joint pain' in illness_lower:
        doctor_name = 'Dr. Jonas'
    else:
        doctor_name = 'Dr. Katherine'

    # Step 3: Format date and time strings for database insertion.
    try:
        start_time_full = datetime.strptime(f"{appointment_date} {appointment_time}", '%Y-%m-%d %H:%M')
        end_time_full = start_time_full + timedelta(minutes=30)
        start_time_str = start_time_full.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time_full.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # This is a fallback and should not be reached if the initial validation is working.
        return {"status": "error", "message": "Invalid internal date or time format."}

    # Step 4: Perform database operations.
    try:
        cur = con.cursor()

        # Check for a conflicting appointment for the same doctor at the same time.
        cur.execute(
            "SELECT AppointmentId FROM Appointments WHERE DoctorName = ? AND AppointmentTimeStart = ?",
            (doctor_name, start_time_str)
        )
        if cur.fetchone():
            conflict_message = f"Sorry, {doctor_name} is already booked at that time. Please choose another slot."
            return {"status": "conflict", "message": conflict_message}

        # Insert the new appointment record.
        cur.execute(
            "INSERT INTO Appointments (PatientId, DoctorName, AppointmentTimeStart, AppointmentTimeEnd) VALUES (?, ?, ?, ?)",
            (patient_id, doctor_name, start_time_str, end_time_str)
        )
        con.commit()
        appointment_id = cur.lastrowid
        
        # UI Confirmation
        print("\n---")
        print(f"SYSTEM: Appointment {appointment_id} created for patient {patient_id}.")
        print("SYSTEM: Triggering email confirmation...")
        print("---\n")
        
        # Fetch patient details for the confirmation email.
        cur.execute("SELECT PatientEmail, PatientName FROM Patients WHERE PatientId = ?", (patient_id,))
        patient_info = cur.fetchone()
        
        if patient_info:
            patient_email, patient_name = patient_info
            send_appointment_confirmation(
                patient_email=patient_email,
                patient_name=patient_name,
                doctor_name=doctor_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time
            )
        else:
            print(f"Warning: Could not find details for patient ID {patient_id} to send confirmation email.")

        # Return a success message.
        return {
            "status": "success",
            "appointment_id": appointment_id,
            "doctor_name": doctor_name,
            "time": appointment_time,
            "message": f"Appointment successfully booked with {doctor_name} at {appointment_time}."
        }

    except sqlite3.Error as e:
        print(f"Database appointment booking error: {e}")
        return {"status": "error", "message": "A database error occurred while booking the appointment."}

def reschedule_appointment(con, patient_id, old_appointment_date, old_appointment_time, new_appointment_date, new_appointment_time):
    """
    Reschedules an existing appointment by canceling the old one and booking a new one.
    This is an atomic operation: it first checks for availability before making any changes.
    """
    # 0. Validate the new date and time before doing anything else
    is_valid, message = is_valid_appointment_datetime(new_appointment_date, new_appointment_time)
    if not is_valid:
        return {"status": "error", "message": f"The new appointment time is invalid. Reason: {message}"}

    try:
        # 1. Find the original appointment to get details like doctor and illness
        old_start_time_full = datetime.strptime(f"{old_appointment_date} {old_appointment_time}", '%Y-%m-%d %H:%M')
        old_start_time_str = old_start_time_full.strftime('%Y-%m-%d %H:%M:%S')

        cur = con.cursor()
        cur.execute(
            "SELECT a.AppointmentId, a.DoctorName, p.PatientIllness, p.PatientEmail, p.PatientName FROM Appointments a JOIN Patients p ON a.PatientId = p.PatientId WHERE a.PatientId = ? AND a.AppointmentTimeStart = ?",
            (patient_id, old_start_time_str)
        )
        original_appointment = cur.fetchone()

        if not original_appointment:
            return {"status": "not_found", "message": "The original appointment to reschedule was not found."}

        appointment_id, doctor_name, illness, patient_email, patient_name = original_appointment

        # 2. Check availability for the new slot with the same doctor
        availability_result = check_availability(con, new_appointment_date, new_appointment_time, illness)
        if availability_result["status"] != "available":
            return {"status": "conflict", "message": f"The new time slot is not available. Reason: {availability_result['message']}"}

        # 3. The new slot is available, so proceed with rescheduling.
        # This involves deleting the old appointment and booking the new one.
        
        # Delete the old appointment
        cur.execute("DELETE FROM Appointments WHERE AppointmentId = ?", (appointment_id,))
        
        # Book the new appointment using the existing book_appointment logic's core
        new_start_time_full = datetime.strptime(f"{new_appointment_date} {new_appointment_time}", '%Y-%m-%d %H:%M')
        new_end_time_full = new_start_time_full + timedelta(minutes=30)
        new_start_time_str = new_start_time_full.strftime('%Y-%m-%d %H:%M:%S')
        new_end_time_str = new_end_time_full.strftime('%Y-%m-%d %H:%M:%S')

        cur.execute(
            "INSERT INTO Appointments (PatientId, DoctorName, AppointmentTimeStart, AppointmentTimeEnd) VALUES (?, ?, ?, ?)",
            (patient_id, doctor_name, new_start_time_str, new_end_time_str)
        )
        
        con.commit()
        new_appointment_id = cur.lastrowid
        
        # System confirmation message for the UI
        print("\n---")
        print(f"SYSTEM: Appointment rescheduled for patient {patient_id}. New ID is {new_appointment_id}.")
        print("SYSTEM: Triggering email confirmation...")
        print("---\n")
        
        # Send confirmation email for the new appointment
        send_appointment_confirmation(
            patient_email=patient_email,
            patient_name=patient_name,
            doctor_name=doctor_name,
            appointment_date=new_appointment_date,
            appointment_time=new_appointment_time
        )

        return {
            "status": "success",
            "message": f"Your appointment has been successfully rescheduled to {new_appointment_date} at {new_appointment_time} with {doctor_name}."
        }

    except sqlite3.Error as e:
        con.rollback() # Roll back any changes if an error occurs
        print(f"Database rescheduling error: {e}")
        return {"status": "error", "message": "A database error occurred during the rescheduling process."}
    except ValueError:
        return {"status": "error", "message": "Invalid date or time format provided."}

def check_insurance_coverage(con, insurance_name):
    """
    Queries the database to check for insurance coverage, using fuzzy matching for the provider name.
    """
    try:
        cur = con.cursor()
        
        # Get all insurance names from the database
        cur.execute("SELECT InsuranceName FROM Insurance")
        all_insurance_names = [row[0] for row in cur.fetchall()]

        # Find the best match for the provided insurance name
        best_match, score = process.extractOne(insurance_name, all_insurance_names)

        # If the match score is low, assume it's not a valid name
        if score < 80:
            return {
                "status": "not_found",
                "message": "This insurance provider is not in our list. However, we can still proceed with scheduling an appointment."
            }
        
        # Query the database using the best match
        cur.execute("SELECT InsuranceName, IsSupported, DiseasesCovered FROM Insurance WHERE InsuranceName = ?", (best_match,))
        result = cur.fetchone()

        if not result:
            # This should ideally not happen if the fuzzy match is working correctly
            return {"status": "error", "message": "Could not retrieve details for the matched insurance."}

        name, is_supported, diseases_covered = result
        
        if not is_supported:
            return {
                "status": "not_supported",
                "name": name,
                "message": f"While {name} is in our system, we do not currently support it. We can still schedule an appointment, but you would need to cover the costs directly."
            }

        # Check for 'General' or 'Orthopedics' coverage
        has_coverage = 'general' in diseases_covered.lower() or 'orthopedics' in diseases_covered.lower()
        
        if has_coverage:
            return {
                "status": "supported_and_covers",
                "name": name,
                "message": f"Yes, we accept {name}, and it appears to cover the relevant services. We can proceed with your intake."
            }
        else:
            return {
                "status": "supported_but_coverage_unclear",
                "name": name,
                "message": f"Yes, we accept {name}. However, for your specific needs (Orthopedics), we would recommend you confirm the coverage details directly with them. We can still proceed with the intake process."
            }

    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        return {"status": "error", "message": "There was an error checking the insurance details."}

def initialize_database():
    """
    Initializes a SQLite database file and creates the necessary tables.
    Returns the database connection object.
    """
    try:
        # Create a database file
        con = sqlite3.connect("clinic_data.db", check_same_thread=False)
        cur = con.cursor()

        # Check if tables already exist to avoid re-populating
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Insurance'")
        if cur.fetchone() is None:
            # Create the Insurance table first
            cur.execute("""
                CREATE TABLE Insurance (
                    InsuranceId INTEGER PRIMARY KEY,
                    InsuranceName TEXT NOT NULL,
                    IsSupported INTEGER NOT NULL, -- Using 1 for Yes, 0 for No
                    DiseasesCovered TEXT
                )
            """)

            # Create the Patients table
            cur.execute("""
                CREATE TABLE Patients (
                    PatientId INTEGER PRIMARY KEY AUTOINCREMENT,
                    PatientName TEXT,
                    PatientPhoneNumber TEXT,
                    PatientEmail TEXT UNIQUE,
                    PatientIllness TEXT,
                    InsuranceId INTEGER,
                    FOREIGN KEY (InsuranceId) REFERENCES Insurance(InsuranceId)
                )
            """)

            # Create the Appointments table
            cur.execute("""
                CREATE TABLE Appointments (
                    AppointmentId INTEGER PRIMARY KEY AUTOINCREMENT,
                    AppointmentTimeStart TEXT,
                    AppointmentTimeEnd TEXT,
                    DoctorName TEXT,
                    PatientId INTEGER,
                    FOREIGN KEY (PatientId) REFERENCES Patients(PatientId)
                )
            """)
            
            # Populate the insurance table with initial data
            populate_insurance_data(con)
            print("Database created and insurance data populated.")
        else:
            print("Database file already exists. Skipping table creation.")
        
        print("SQLite database initialized successfully.")
        return con

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

if __name__ == '__main__':
    # A simple test to initialize the database and check if tables were created
    db_connection = initialize_database()
    if db_connection:
        cursor = db_connection.cursor()
        
        # Verify that the tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nTables in the database:")
        for table in tables:
            print(f"- {table[0]}")
            
            # Print the schema of each table
            cursor.execute(f"PRAGMA table_info({table[0]});")
            schema = cursor.fetchall()
            print("  Schema:")
            for column in schema:
                print(f"    - {column[1]} ({column[2]})")
        
        # Verify that the Insurance table is populated
        print("\nInsurance Data:")
        cursor.execute("SELECT * FROM Insurance LIMIT 5;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)

        db_connection.close() 