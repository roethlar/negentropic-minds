# json_to_markdown.py

import json
import datetime

# --- Configuration ---
# The name of the input JSON file you want to convert.
# Make sure this file is in the same folder as this script.
INPUT_FILENAME = "Reformatted-Grok-Claudia.ai-ClaudiaGPT_exchange_1.json"

# The name of the output Markdown file that will be created.
OUTPUT_FILENAME = "Grok-Claudia-Conversation.md"


# --- Main Script Logic ---

def convert_json_to_markdown(input_file, output_file):
    """
    Reads a conversation log from a JSON file and converts it to a
    human-readable Markdown format.
    """
    print(f"Reading data from '{input_file}'...")

    try:
        # Open and load the JSON data from the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"--- ERROR ---")
        print(f"The input file '{input_file}' was not found.")
        print("Please make sure the file exists in the same directory.")
        return
    except json.JSONDecodeError:
        print(f"--- ERROR ---")
        print(f"The file '{input_file}' is not a valid JSON file.")
        return

    # --- Start writing to the Markdown file ---
    # 'w' mode means we create a new file or overwrite an existing one.
    with open(output_file, 'w', encoding='utf-8') as f:
        
        # Write the main title from the metadata
        if 'meta' in data and 'title' in data['meta']:
            f.write(f"# {data['meta']['title']}\n\n")

        # Write some key metadata from the 'meta' object
        if 'meta' in data:
            meta = data['meta']
            f.write("## Session Details\n\n")
            f.write(f"- **Date:** {meta.get('date', 'N/A')}\n")
            f.write(f"- **Facilitator:** {meta.get('facilitator', 'N/A')}\n")
            
            # Format participants list if it exists
            participants = meta.get('participants', [])
            if participants:
                f.write("- **Participants:**\n")
                for p in participants:
                    f.write(f"  - {p}\n")
            f.write("\n") # Add a newline for spacing

        # --- Write the Conversation History ---
        f.write("## Conversation Log\n\n")

        # Check if the 'messages' key exists
        if 'messages' in data and data['messages']:
            # Loop through each message in the conversation history
            for message in data['messages']:
                speaker = message.get('speaker', 'Unknown')
                text = message.get('text', '[no content]')
                
                # Write the speaker's name as a bold heading
                f.write(f"**{speaker}:**\n\n")
                
                # Write the message text. We replace newline characters
                # in the JSON with Markdown-style paragraphs for readability.
                formatted_text = text.replace('\n', '\n\n')
                f.write(f"{formatted_text}\n\n")
                
                # Add a horizontal rule for separation between speakers
                f.write("---\n\n")
        else:
            f.write("No conversation messages found in the JSON file.\n")
    
    print(f"Conversion complete. Markdown file saved as '{output_file}'")


# --- Run the conversion ---
if __name__ == "__main__":
    convert_json_to_markdown(INPUT_FILENAME, OUTPUT_FILENAME)
