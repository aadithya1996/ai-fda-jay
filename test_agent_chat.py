import openai
import os
import json
from dotenv import load_dotenv
import csv
import pytz
from datetime import datetime
from database import (
    initialize_database, check_insurance_coverage, add_patient, 
    get_patient_details, book_appointment, cancel_appointment,
    update_patient, reschedule_appointment
)
import soundfile as sf
import sounddevice as sd

# --- Initialization ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
db_connection = initialize_database()

def create_system_prompt():
    """
    Creates the initial system prompt by reading a template and injecting FAQ and current date.
    """
    timezone = pytz.timezone('America/New_York')
    now = datetime.now(timezone)
    current_date = now.strftime('%Y-%m-%d')
    current_day = now.strftime('%A')

    with open('prompt_template.txt', 'r') as f:
        prompt_template = f.read()

    faq_string = ""
    with open('faq.csv', 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            faq_string += f"Q: {row[1]}\nA: {row[2]}\n\n"
    
    return prompt_template.format(
        faq_content=faq_string.strip(),
        current_date=current_date,
        current_day=current_day
    )

def play_audio(data, fs):
    """
    Helper function to play audio data.
    """
    sd.play(data, fs)
    sd.wait()

def run_chat_test():
    """
    Runs an interactive, text-based chat simulation to test the agent's logic.
    """
    print("--- Starting Agent Chat Simulation ---")
    print("Type 'exit' to end the conversation.")
    
    conversation_history = [{"role": "system", "content": create_system_prompt()}]
    
    initial_greeting = "Hello, thank you for calling Stemmee Surgery Center. My name is Jay. How can I help you today?"
    print(f"\nJay: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})

    tools = [
        # NOTE: This tool list must be kept in sync with main.py
        {"type": "function", "function": {"name": "check_insurance_coverage", "description": "Checks if a patient's insurance is supported...", "parameters": {"type": "object", "properties": {"insurance_name": {"type": "string"}}, "required": ["insurance_name"]}}},
        {"type": "function", "function": {"name": "add_patient", "description": "Adds a new patient record...", "parameters": {"type": "object", "properties": {"patient_name": {"type": "string"}, "phone_number": {"type": "string"}, "patient_email": {"type": "string"}, "illness": {"type": "string"}, "insurance_name": {"type": "string"}}, "required": ["patient_name", "phone_number", "patient_email", "illness", "insurance_name"]}}},
        {"type": "function", "function": {"name": "get_patient_details", "description": "Looks up an existing patient...", "parameters": {"type": "object", "properties": {"patient_name": {"type": "string"}, "patient_email": {"type": "string"}}, "required": ["patient_name", "patient_email"]}}},
        {"type": "function", "function": {"name": "book_appointment", "description": "Books an appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "appointment_date": {"type": "string"}, "appointment_time": {"type": "string"}, "illness": {"type": "string"}}, "required": ["patient_id", "appointment_date", "appointment_time", "illness"]}}},
        {"type": "function", "function": {"name": "cancel_appointment", "description": "Cancels an existing appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "appointment_date": {"type": "string"}, "appointment_time": {"type": "string"}}, "required": ["patient_id", "appointment_date", "appointment_time"]}}},
        {"type": "function", "function": {"name": "update_patient", "description": "Updates a patient's record...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "new_phone_number": {"type": "string"}, "new_insurance_name": {"type": "string"}, "new_patient_email": {"type": "string"}}, "required": ["patient_id"]}}},
        {"type": "function", "function": {"name": "reschedule_appointment", "description": "Reschedules an existing appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "old_appointment_date": {"type": "string"}, "old_appointment_time": {"type": "string"}, "new_appointment_date": {"type": "string"}, "new_appointment_time": {"type": "string"}}, "required": ["patient_id", "old_appointment_date", "old_appointment_time", "new_appointment_date", "new_appointment_time"]}}}
    ]

    available_functions = {
        "check_insurance_coverage": check_insurance_coverage, "add_patient": add_patient,
        "get_patient_details": get_patient_details, "book_appointment": book_appointment,
        "cancel_appointment": cancel_appointment, "update_patient": update_patient,
        "reschedule_appointment": reschedule_appointment
    }

    while True:
        user_message = input("\nYou: ")
        if user_message.lower() == 'exit':
            break
        
        conversation_history.append({"role": "user", "content": user_message})

        try:
            response = openai.chat.completions.create(
                model="gpt-4o", messages=conversation_history, tools=tools, tool_choice="auto"
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                interim_message = response_message.content
                if interim_message:
                    print(f"Jay (interim): {interim_message}")
                    # In a real scenario, TTS and play this message.
                    # For this test script, we'll just print it.
                
                conversation_history.append(response_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    print(f"--- Agent wants to call function: {function_name} ---")
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    
                    function_response = function_to_call(con=db_connection, **function_args)
                    
                    print(f"--- Function Result: {function_response} ---")
                    
                    conversation_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    })
                
                second_response = openai.chat.completions.create(model="gpt-4o", messages=conversation_history)
                assistant_message = second_response.choices[0].message.content
            else:
                assistant_message = response_message.content

            print(f"\nJay: {assistant_message}")
            if assistant_message:
                conversation_history.append({"role": "assistant", "content": assistant_message})

        except Exception as e:
            print(f"An error occurred: {e}")

    db_connection.close()
    print("\n--- Simulation Ended. Database connection closed. ---")

if __name__ == "__main__":
    run_chat_test() 