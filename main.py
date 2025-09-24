import openai
import sounddevice as sd
import soundfile as sf
import numpy as np
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

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

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

conversation_history = [
    {"role": "system", "content": create_system_prompt()}
]

db_connection = initialize_database()

tools = [
    {"type": "function", "function": {"name": "check_insurance_coverage", "description": "Checks if a patient's insurance is supported...", "parameters": {"type": "object", "properties": {"insurance_name": {"type": "string"}}, "required": ["insurance_name"]}}},
    {"type": "function", "function": {"name": "add_patient", "description": "Adds a new patient record...", "parameters": {"type": "object", "properties": {"patient_name": {"type": "string"}, "phone_number": {"type": "string"}, "patient_email": {"type": "string"}, "illness": {"type": "string"}, "insurance_name": {"type": "string"}}, "required": ["patient_name", "phone_number", "patient_email", "illness", "insurance_name"]}}},
    {"type": "function", "function": {"name": "get_patient_details", "description": "Looks up an existing patient...", "parameters": {"type": "object", "properties": {"patient_name": {"type": "string"}, "patient_email": {"type": "string"}}, "required": ["patient_name", "patient_email"]}}},
    {"type": "function", "function": {"name": "book_appointment", "description": "Books an appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "appointment_date": {"type": "string"}, "appointment_time": {"type": "string"}, "illness": {"type": "string"}}, "required": ["patient_id", "appointment_date", "appointment_time", "illness"]}}},
    {"type": "function", "function": {"name": "cancel_appointment", "description": "Cancels an existing appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "appointment_date": {"type": "string"}, "appointment_time": {"type": "string"}}, "required": ["patient_id", "appointment_date", "appointment_time"]}}},
    {"type": "function", "function": {"name": "update_patient", "description": "Updates a patient's record...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "new_phone_number": {"type": "string"}, "new_insurance_name": {"type": "string"}, "new_patient_email": {"type": "string"}}, "required": ["patient_id"]}}},
    {"type": "function", "function": {"name": "reschedule_appointment", "description": "Reschedules an existing appointment...", "parameters": {"type": "object", "properties": {"patient_id": {"type": "integer"}, "old_appointment_date": {"type": "string"}, "old_appointment_time": {"type": "string"}, "new_appointment_date": {"type": "string"}, "new_appointment_time": {"type": "string"}}, "required": ["patient_id", "old_appointment_date", "old_appointment_time", "new_appointment_date", "new_appointment_time"]}}}
]

def record_audio(fs=44100, channels=1, silence_threshold=0.01, silence_seconds=2.0, max_record_seconds=20):
    """
    Records audio from the microphone, stopping after a period of silence.
    """
    print(f"\nListening... (stops after {silence_seconds}s of silence)")
    check_interval = 15
    blocksize = fs // check_interval
    silent_blocks_needed = int(silence_seconds * check_interval)
    max_blocks = max_record_seconds * check_interval
    pre_buffer_size = check_interval // 2
    
    stream = sd.InputStream(samplerate=fs, channels=channels, blocksize=blocksize, dtype='float32')
    
    recorded_frames = []
    pre_buffer = []
    silent_blocks_count = 0
    recording_started = False
    
    with stream:
        for _ in range(max_blocks):
            audio_chunk, overflowed = stream.read(blocksize)
            rms = np.sqrt(np.mean(audio_chunk**2))
            is_silent = rms < silence_threshold

            if recording_started:
                recorded_frames.append(audio_chunk)
                if is_silent:
                    silent_blocks_count += 1
                else:
                    silent_blocks_count = 0
                
                if silent_blocks_count >= silent_blocks_needed:
                    print("Silence detected. Stopping recording.")
                    break
            else:
                if not is_silent:
                    print("Speech detected, starting recording.")
                    recording_started = True
                    recorded_frames.extend(pre_buffer)
                    recorded_frames.append(audio_chunk)
                else:
                    pre_buffer.append(audio_chunk)
                    if len(pre_buffer) > pre_buffer_size:
                        pre_buffer.pop(0)
        else:
            print("Maximum recording time reached.")

    print("Recording finished.")
    
    if not recorded_frames:
        return np.array([], dtype='float32'), fs
        
    recording = np.concatenate(recorded_frames, axis=0)
    
    num_trailing_silent_frames = silent_blocks_count * blocksize
    if num_trailing_silent_frames > 0 and len(recording) > num_trailing_silent_frames:
        recording = recording[:-num_trailing_silent_frames]

    return recording, fs

def play_audio(data, fs):
    """Plays back audio."""
    print("Playing audio...")
    sd.play(data, fs)
    sd.wait()
    print("Playback finished.")

def main():
    initial_greeting = "Hello, thank you for calling Stemmee Surgery Center. My name is Jay. How can I help you today?"
    print(f"\nJay: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})

    try:
        with openai.audio.speech.with_streaming_response.create(
            model="tts-1", voice="alloy", input=initial_greeting,
        ) as response:
            response.stream_to_file("greeting.mp3")
        data, fs = sf.read("greeting.mp3")
        play_audio(data, fs)
    except Exception as e:
        print(f"An error occurred during the initial greeting: {e}")
    finally:
        if os.path.exists("greeting.mp3"):
            os.remove("greeting.mp3")

    try:
        while True:
            audio_data, sample_rate = record_audio()

            if audio_data.size == 0:
                print("No audio recorded, listening again.")
                continue
            
            temp_file = "temp_recording.wav"
            sf.write(temp_file, audio_data, sample_rate)

            try:
                with open(temp_file, "rb") as audio_file:
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                
                user_message = transcript.text
                print(f"You said: {user_message}")

                if "goodbye" in user_message.lower():
                    print("Goodbye!")
                    break

                conversation_history.append({"role": "user", "content": user_message})

                print("Sending to OpenAI...")
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=conversation_history,
                    tools=tools,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                if tool_calls:
                    interim_message = response_message.content
                    if interim_message:
                        print(f"Jay (interim): {interim_message}")
                        with openai.audio.speech.with_streaming_response.create(
                            model="tts-1", voice="alloy", input=interim_message
                        ) as interim_response:
                            interim_response.stream_to_file("interim_response.mp3")
                        data, fs = sf.read("interim_response.mp3")
                        play_audio(data, fs)
                        os.remove("interim_response.mp3")

                    available_functions = {
                        "check_insurance_coverage": check_insurance_coverage,
                        "add_patient": add_patient,
                        "get_patient_details": get_patient_details,
                        "book_appointment": book_appointment,
                        "cancel_appointment": cancel_appointment,
                        "update_patient": update_patient,
                        "reschedule_appointment": reschedule_appointment,
                    }
                    
                    conversation_history.append(response_message)
                    
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_to_call = available_functions[function_name]
                        function_args = json.loads(tool_call.function.arguments)
                        
                        function_response = function_to_call(con=db_connection, **function_args)
                        
                        conversation_history.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(function_response),
                            })
                    
                    second_response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=conversation_history,
                    )
                    assistant_message = second_response.choices[0].message.content
                else:
                    assistant_message = response_message.content

                print(f"OpenAI said: {assistant_message}")

                if assistant_message:
                    conversation_history.append({"role": "assistant", "content": assistant_message})

                with openai.audio.speech.with_streaming_response.create(
                    model="tts-1",
                    voice="alloy",
                    input=assistant_message,
                ) as response:
                    response.stream_to_file("response.mp3")

                data, fs = sf.read("response.mp3")
                play_audio(data, fs)

            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                if os.path.exists("response.mp3"):
                    os.remove("response.mp3")
    finally:
        if db_connection:
            db_connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()
