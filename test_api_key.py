import openai
import os
from dotenv import load_dotenv

def test_openai_api_key():
    """
    Tests if the OpenAI API key is valid by making a simple API call.
    """
    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in .env file.")
            return

        print("Testing OpenAI API key...")
        client = openai.OpenAI(api_key=api_key)
        
        # Make a simple, low-cost API call to check for authentication
        client.models.list()
        
        print("✅ OpenAI API key is valid!")

    except openai.AuthenticationError:
        print("❌ Error: Invalid OpenAI API key. Please check your .env file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_openai_api_key() 