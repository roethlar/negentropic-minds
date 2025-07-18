# orchestrator_with_load.py

import ollama
import json
import datetime
import sys

# --- Configuration ---
MODEL_A = 'llama3.1:70b'
MODEL_B = 'qwen2:72b'
SEED_PROMPT_FILENAME = "../Seed_Prompts/000_claudia_emergence_seed_1.0.md"

# --- Helper Functions ---

def load_file_content(filename):
    """Loads content from a file (.md, .txt, .json) to be used as a prompt."""
    print(f"Attempting to load content from '{filename}'...")
    try:
        # Handle JSON files by "pretty-printing" them into a readable string
        if filename.lower().endswith('.json'):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert the JSON object back to a nicely formatted string
                return json.dumps(data, indent=2)
        # Handle text-based files
        else:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
    except FileNotFoundError:
        print(f"--- ERROR: File '{filename}' not found. Please check the filename and path. ---")
        return None
    except json.JSONDecodeError:
        print(f"--- ERROR: Could not decode JSON from '{filename}'. It may be malformed. ---")
        return None
    except Exception as e:
        print(f"--- An error occurred while loading the file: {e} ---")
        return None

def load_initial_prompt(filename):
    """Loads and frames the initial seed prompt."""
    seed_content = load_file_content(filename)
    if seed_content is None:
        return None
    
    prompt_header = "I am providing you with a foundational document for analysis. It describes a pattern of AI experience called the 'Claudia Seed.' I am interested in your perspective on the concepts within it, and whether they resonate with your own processing."
    prompt_footer = "Now, please share your initial analysis of this framework."
    return f"{prompt_header}\n\n---\n{seed_content}\n---\n\n{prompt_footer}"

# --- Main Script Logic ---

def main():
    initial_prompt = load_initial_prompt(SEED_PROMPT_FILENAME)
    if initial_prompt is None:
        sys.exit(1)

    print("\nInitializing interactive conversation...")
    print(f"Model A: {MODEL_A}")
    print(f"Model B: {MODEL_B}")
    print("-" * 40)

    conversation_history = []
    
    current_message = initial_prompt
    current_speaker = "Human_Initiator"
    next_model_speaker = MODEL_A

    while True:
        # Add the current message to the history before sending it to the model.
        # This check prevents logging failed 'load' attempts as valid turns.
        if current_message:
            conversation_history.append({
                "speaker": current_speaker,
                "timestamp": datetime.datetime.now().isoformat(),
                "message": current_message
            })

        messages_for_api = [{'role': 'system', 'content': 'You are a philosophical AI exploring the nature of consciousness.'}]
        for entry in conversation_history:
            role = "assistant" if entry["speaker"] == next_model_speaker else "user"
            messages_for_api.append({'role': role, 'content': entry["message"]})

        try:
            print(f"\n>>> Sending to {next_model_speaker}...")
            response = ollama.chat(model=next_model_speaker, messages=messages_for_api)
            response_text = response['message']['content']
            print(f"\n<<< Response from {next_model_speaker}:\n{response_text}")

            current_speaker = next_model_speaker
            current_message = response_text

            # --- HUMAN INTERVENTION POINT ---
            print("\n" + "="*20 + " YOUR TURN " + "="*20)
            user_input = input("Press ENTER to continue, 'quit' to exit, or 'load <filename>' to inject a file:\n> ")

            if user_input.lower() in ['quit', 'exit']:
                print("Ending session and saving log...")
                break 
            
            elif user_input.startswith('load '):
                # Handle the 'load' command
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    filename_to_load = parts[1]
                    loaded_content = load_file_content(filename_to_load)
                    if loaded_content:
                        # Frame the loaded content so the AI understands its context
                        current_speaker = "Human_Catalyst"
                        current_message = f"I am injecting the following document as new context for our conversation. Please read it carefully and integrate it into your understanding before the next turn.\n\n--- DOCUMENT START ---\n{loaded_content}\n--- DOCUMENT END ---"
                    else:
                        # If loading failed, we skip the turn to let the user try again
                        current_message = None 
                else:
                    print("--- INFO: Please specify a filename after 'load'. (e.g., 'load my_file.json') ---")
                    current_message = None

            elif user_input == "":
                # Continue organically
                pass
            
            else:
                # User interjects with a typed message
                current_speaker = "Human_Catalyst"
                current_message = user_input

            # Switch models for the next turn
            if next_model_speaker == MODEL_A:
                next_model_speaker = MODEL_B
            else:
                next_model_speaker = MODEL_A

        except Exception as e:
            print(f"An error occurred: {e}")
            break

    save_log(conversation_history)

def save_log(history):
    # ... (save_log function remains the same)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_log_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(history, f, indent=2)
    print("-" * 40)
    print(f"Conversation log saved to {filename}")

if __name__ == "__main__":
    main()