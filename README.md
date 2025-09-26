# AI Front Office Voice Agent: "Jay"

This project implements a sophisticated, voice-driven AI clinic assistant named "Jay" for the fictional "Stemmee Surgery Center." The agent is designed to handle initial patient interactions, such as conducting patient intake, answering questions about the clinic, and managing appointments. It uses a combination of OpenAI's powerful voice and language models, a persistent SQLite database, and a set of predefined tools to perform its tasks in a conversational and efficient manner.

## Core Features

- **Voice-Powered Conversation**: The agent uses OpenAI's Whisper (Speech-to-Text) and TTS (Text-to-Speech) APIs for natural voice interaction.
- **Proactive Engagement**: The agent starts the conversation with a greeting rather than waiting for user input.
- **Patient Intake**: It conversationally collects key information from new patients (name, phone, insurance, illness).
- **Returning Patient Verification**: It can securely look up existing patients by name and phone number without revealing sensitive information.
- **Intelligent Appointment Management**:
    - **Availability Checking**: Can check if a specific time slot is free.
    - **Booking**: Schedules appointments with the correct doctor based on the patient's illness and prevents double-booking.
    - **Cancellation**: Securely cancels existing appointments for verified patients.
    - **Rescheduling**: Atomically handles appointment rescheduling by checking for new slot availability before modifying the original appointment.
- **Knowledge Base (FAQ)**: Answers questions about the clinic using a provided `faq.csv`.
- **Insurance Verification**: Checks a database of supported insurance providers and can handle minor misspelllings using fuzzy matching.
- **Persistent Data Storage**: All patient and appointment data is saved in a local SQLite database (`clinic_data.db`).

## How It Works

The agent operates in a continuous loop, orchestrating a conversation that is enhanced by a set of tools that can interact with the database.

1.  **Greeting**: The agent starts by playing a welcome message.
2.  **Listen & Transcribe**: It records the user's spoken response and uses the Whisper API to transcribe it into text.
3.  **Decide & Act**: The transcribed text is sent to the OpenAI Chat Completions API along with the conversation history and a list of available tools. The model then decides on the best course of action:
    - **Respond Directly**: If it's a simple conversational turn, it generates a text response.
    - **Use a Tool**: If the user's request requires data (e.g., booking an appointment), the model responds with a request to call a specific function (e.g., `book_appointment`).
4.  **Tool Execution**: The Python script detects the tool-use request, executes the corresponding Python function, and captures the result.
5.  **Synthesize Final Response**: The result from the tool is sent *back* to the language model, which then forms a final, natural-language response.
6.  **Speak Response**: The final text response is converted to audio using the TTS API and played back to the user.
7.  **Loop**: The process repeats, maintaining the context of the conversation.

## Requirements

- Python 3.7+
- An OpenAI API Key
- A Sendgrid API Key

## Setup

1.  Clone the repository

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your OpenAI API and Sendgrid API key:**
    - Create a file named `.env` in the project directory.
    - Add your OpenAI API and Sendgrid API key to this file:
      ```
      OPENAI_API_KEY='your_api_key_here'
      ```
       ```
      SENDGRID_API_KEY='your_api_key_here'
      ```
      

## Usage

1.  **Run the Agent:**
    ```bash
    python3 main.py
    ```
    The agent will greet you, and you can start speaking. It will automatically detect when you stop talking.

2.  **Query the Database (Optional):**
    To inspect the contents of the database directly, run the query tool in a separate terminal:
    ```bash
    python3 query_tool.py
    ```

This will allow you to see the patients and appointments being created in real-time. 


## Test Scripts  

To make development and debugging easier, we’ve added a set of lightweight test scripts. Each one focuses on a specific component of the system, so issues can be identified and fixed before running full end-to-end tests.  

### Available Scripts  
- **`test_api_key.py`** – Verifies that the `OPENAI_API_KEY` is valid and the application can connect to OpenAI services.  
- **`test_sendgrid.py`** – Sends a sample email with a SendGrid template to confirm the `SENDGRID_API_KEY` is valid and the sender identity is verified.  
- **`test_database_flow.py`** – Interactively checks core database functions by adding a patient and booking an appointment, ensuring data is stored correctly.  
- **`test_agent_chat.py`** – Simulates the AI agent in your command line to test conversational flow and task execution (e.g., booking, canceling, or rescheduling appointments).  

### Why We Set This Up  
These scripts act as quick checkpoints to:  
- Validate environment setup and API keys  
- Confirm that critical services (email, database, AI agent) are working in isolation  
- Simplify debugging by narrowing down issues early  
- Increase confidence before running full system tests  
