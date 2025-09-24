import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file, so this module is self-contained
load_dotenv()

def send_appointment_confirmation(patient_email, patient_name, doctor_name, appointment_date, appointment_time):
    """
    Sends a confirmation email to the patient using a SendGrid dynamic template.
    """
    # Ensure the SendGrid API key is set in the environment variables
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_api_key:
        print("Warning: SENDGRID_API_KEY not found. Skipping email notification.")
        return

    # IMPORTANT: This must be the email address you verified in your SendGrid account.
    from_email = "2023hb21247@wilp.bits-pilani.ac.in"

    message = Mail(
        from_email=from_email,
        to_emails=patient_email)

    # --- Data Formatting for the Template ---
    # Convert the raw date and time into more human-readable formats.
    try:
        # Format date from 'YYYY-MM-DD' to 'Month Day, Year' (e.g., 'October 15, 2025')
        date_obj = datetime.strptime(appointment_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%B %d, %Y')

        # Format time from 'HH:MM' (24-hour) to 'H:MM AM/PM' (e.g., '10:00 AM')
        time_obj = datetime.strptime(appointment_time, '%H:%M')
        formatted_time = time_obj.strftime('%I:%M %p').lstrip('0')
    except ValueError:
        # If formatting fails, fall back to the raw data to ensure the email still sends.
        formatted_date = appointment_date
        formatted_time = appointment_time

    # Set the dynamic template ID and the data for the template, matching the user's required fields.
    message.template_id = 'd-6245e3018e5b430f98f27cbb96a1dd08'
    message.dynamic_template_data = {
        'appointment_start_time': formatted_time,
        'patient_name': patient_name,
        'doctor_name': doctor_name,
        'appointment_date': formatted_date,
        # NOTE: Unsubscribe links are placeholders as they are typically generated per user in a full application.
        'unsubscribe': "https://example.com/unsubscribe",
        'unsubscribe_preferences': "https://example.com/preferences"
    }

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(f"Confirmation email sent to {patient_email}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending confirmation email: {e}")

if __name__ == '__main__':
    # A simple test to send a sample email.
    # Make sure to set your SENDGRID_API_KEY in your .env file before running this test.
    # Replace the placeholder email with a real one to test.
    print("Sending a test appointment confirmation email...")
    send_appointment_confirmation(
        patient_email='test@example.com',  # Replace with a recipient email for testing
        patient_name='Test Patient',
        doctor_name='Dr. Jonas',
        appointment_date='2023-10-28',
        appointment_time='10:00 AM'
    ) 