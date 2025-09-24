import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_test_email():
    """
    Sends a simple, non-templated email via SendGrid to test API key and sender verification.
    """
    print("--- Starting SendGrid Test ---")
    
    # Load environment variables from .env file
    load_dotenv()
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

    if not sendgrid_api_key:
        print("\nERROR: SENDGRID_API_KEY not found in .env file.")
        print("Please ensure your .env file is correctly set up.")
        return

    # --- Configuration ---
    # IMPORTANT: Replace these placeholders with your actual email addresses.
    # This MUST be the email address you verified as a "Sender Identity" in your SendGrid account.
    from_email = "2023hb21247@wilp.bits-pilani.ac.in" 
    # This can be any email address where you want to receive the test.
    to_email = "aadithya1996@gmail.com" 

    # --- Create the Email Message using a Dynamic Template ---
    message = Mail(
        from_email=from_email,
        to_emails=to_email)

    # Set the dynamic template ID and the data for the template.
    # This data must match the merge variables used in your SendGrid template.
    message.template_id = 'd-6245e3018e5b430f98f27cbb96a1dd08'
    message.dynamic_template_data = {
        'appointment_start_time': "10:00 AM",
        'patient_name': "Test Patient",
        'doctor_name': "Dr. Emily Carter",
        'appointment_date': "October 28, 2025",
        'unsubscribe': "https://example.com/unsubscribe",
        'unsubscribe_preferences': "https://example.com/preferences"
    }

    # --- Send the Email ---
    try:
        print(f"\nAttempting to send a TEMPLATED email from '{from_email}' to '{to_email}'...")
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        print("\n--- RESULT ---")
        if 200 <= response.status_code < 300:
            print("SUCCESS: Email sent successfully!")
            print(f"  - Status Code: {response.status_code}")
            print("Please check the recipient's inbox.")
        else:
            print("ERROR: Failed to send email.")
            print(f"  - Status Code: {response.status_code}")
            print(f"  - Response Body: {response.body}")
            print(f"  - Response Headers: {response.headers}")

    except Exception as e:
        print("\n--- EXCEPTION ---")
        print(f"An unexpected error occurred: {e}")
        print("\nPlease check your API key and sender verification in your SendGrid account.")

if __name__ == "__main__":
    send_test_email() 