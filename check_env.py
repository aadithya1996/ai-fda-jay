import os
from dotenv import load_dotenv

def check_environment_variables():
    """
    Loads environment variables from a .env file and checks for the SENDGRID_API_KEY.
    """
    print("--- Environment Variable Check ---")
    
    # Attempt to load the .env file
    # The dotenv library will search for a .env file in the current directory or parent directories.
    load_dotenv()
    print("Attempted to load variables from .env file.")

    # Get the SendGrid API key from the environment
    sendgrid_key = os.getenv("SENDGRID_API_KEY")

    if sendgrid_key:
        print("\nSUCCESS: SENDGRID_API_KEY was found.")
        # For security, we only show the first few and last few characters
        print(f"  - Key: {sendgrid_key[:4]}...{sendgrid_key[-4:]}")
    else:
        print("\nERROR: SENDGRID_API_KEY was NOT found in the environment.")

    # For debugging, let's print all loaded environment variables
    print("\n--- All Loaded Environment Variables ---")
    # We filter out very long or sensitive-looking values for a cleaner display
    for key, value in os.environ.items():
        if len(value) > 80 or "key" in key.lower() or "secret" in key.lower():
            if key == "SENDGRID_API_KEY": # We already handled this one
                continue
            print(f"- {key}: [value is long or sensitive, not shown]")
        else:
            print(f"- {key}: {value}")
    
    print("\n--- End of Check ---")
    print("\nIf the key was not found, please ensure:")
    print("1. The .env file is in the same directory as this script.")
    print("2. The key is spelled exactly as SENDGRID_API_KEY in the .env file.")
    print("3. There are no extra spaces or quotes around the key or value (e.g., SENDGRID_API_KEY='your_key' is correct).")


if __name__ == "__main__":
    check_environment_variables() 