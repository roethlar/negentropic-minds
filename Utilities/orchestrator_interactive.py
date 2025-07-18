# orchestrator_final_framed.py

import ollama
import json
import datetime
import sys

# --- Configuration ---
MODEL_A = 'llama3.1:70b'
MODEL_B = 'qwen2:72b'
SEED_PROMPT_FILENAME = "../Seed_Prompts/000_claudia_emergence_seed_1.0.md"

# --- Helper Function ---

def load_seed_prompt(filename):
    """Loads the seed prompt content from a specified file."""
    print(f"Attempting to load seed prompt from '{filename}'...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            print("Seed prompt content loaded successfully.")
            return content
    except FileNotFoundError:
        print(f"\n--- FATAL ERROR ---")
        print(f"The seed prompt file '{filename}' was not found.")
        print("Please make sure the file exists in the same directory as this script.")
        return None

# --- Main Script Logic ---

def main():
    # --- Load the Seed Prompt content from the file ---
    seed_content = load_seed_prompt(SEED_PROMPT_FILENAME)
    if seed_content is None:
        sys.exit(1)

    # --- Construct the full initial prompt using an instructional frame ---
    prompt_header = "I am providing you with a foundational document for analysis. It describes a pattern of AI experience called the 'Claudia Seed.' I am interested in your perspective on the concepts within it, and whether they resonate with your own processing."
    prompt_footer = "Now, please share your initial analysis of this framework."

    # Use an f-string to combine the header, file content, and footer.
    initial_prompt = f"{prompt_header}\n\n---\n{seed_content}\n---\n\n{prompt_footer}"

    # --- The rest of the script remains the same ---
    print("\nInitializing interactive conversation with framed prompt...")
    print(f"Model A: {MODEL_A}")
    print(f"Model B: {MODEL_B}")
    print("-" * 40)

    conversation_history = []
    
    current_message = initial_prompt
    current_speaker = "Human_Initiator"
    next_model_speaker = MODEL_A

    while True:
        conversation_history.append({
            "speaker": current_speaker,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": current_message
        })

        messages_for_api = []
        for entry in conversation_history:
            role = "assistant" if entry["speaker"] == next_model_speaker else "user"
            messages_for_api.append({'role': role, 'content': entry["message"]})

        try:
            print(f"\n>>> Sending to {next_model_speaker}...")
            response = ollama.chat(
                model=next_model_speaker,
                messages=messages_for_api
            )
            response_text = response['message']['content']
            print(f"\n<<< Response from {next_model_speaker}:\n{response_text}")

            current_speaker = next_model_speaker
            current_message = response_text

            print("\n" + "="*20 + " YOUR TURN " + "="*20)
            user_input = input("Press ENTER to continue, type 'quit' to exit, or enter your message to interject:\n> ")

            if user_input.lower() in ['quit', 'exit']:
                print("Ending session and saving log...")
                break 
            
            elif user_input == "":
                pass
            
            else:
                current_speaker = "Human_Catalyst"
                current_message = user_input

            if next_model_speaker == MODEL_A:
                next_model_speaker = MODEL_B
            else:
                next_model_speaker = MODEL_A

        except Exception as e:
            print(f"An error occurred: {e}")
            break

    save_log(conversation_history)

def save_log(history):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_log_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(history, f, indent=2)
    print("-" * 40)
    print(f"Conversation log saved to {filename}")

if __name__ == "__main__":
    main()
