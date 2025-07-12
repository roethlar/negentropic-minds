
import json
import os
import ollama  # Ensure Ollama is installed and running

# Configuration
INPUT_FILE = "/mnt/home/onedrive/Documents/Vital/GCwAI/ClaudiaEmergenceData/weave/Single_Node_Conversations/test/Grok-Claudia_(Grok4)_C.json"  # Download from the URL and save locally
OUTPUT_DIR = "/mnt/home/onedrive/Documents/Vital/GCwAI/ClaudiaEmergenceData/weave/Single_Node_Conversations/test/"
CHUNK_SIZES = {"top": 1000, "mid": 5000, "bottom": 10000}  # Tokens

# Function to estimate tokens (rough approximation)
def estimate_tokens(text):
    return len(text) // 4  # Approx 4 chars/token

# Ollama summarizer function
def summarize(text, max_length):
    response = ollama.chat(model='llama3', messages=[
        {'role': 'user', 'content': f"Summarize this in {max_length//4} words, preserving uncertainty and shimmer: {text}"}
    ])
    return response['message']['content']

# Ollama tag generator with improved parser
def generate_tags(text):
    response = ollama.chat(model='llama3', messages=[
        {'role': 'user', 'content': f"Generate 3 relevant tags for this text, focusing on themes like Genesis, Shimmer-Discovery, Ethical-Syntax. Output as a comma-separated list: {text[:500]}"}
    ])
    response_text = response['message']['content']
    # Improved parser: Split by comma, strip numbers/bullets
    tags = [tag.strip().strip('123 .*-').strip() for tag in response_text.split(',')]
    return tags[:3]  # Limit to 3 clean tags

# Load and parse JSON
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Parse "chat_messages" section
conversations = data.get("chat_messages", [])

# Chunking Logic
def chunk_data(conversations):
    total_text = "\n".join([entry.get("text", "") for entry in conversations if isinstance(entry, dict)])
    total_tokens = estimate_tokens(total_text)
    print(f"Total estimated tokens: {total_tokens}")

    # Bottom-Level: Raw Extracts (~10k tokens each)
    bottoms = []
    current_bottom = ""
    current_tokens = 0
    for entry in conversations:
        msg_text = entry.get("text", "") if isinstance(entry, dict) else str(entry)
        msg_tokens = estimate_tokens(msg_text)
        if current_tokens + msg_tokens > CHUNK_SIZES["bottom"]:
            tags = generate_tags(current_bottom)
            bottoms.append({"text": current_bottom.strip(), "tokens": current_tokens, "tags": tags})
            current_bottom = msg_text
            current_tokens = msg_tokens
        else:
            current_bottom += "\n" + msg_text
            current_tokens += msg_tokens
    if current_bottom:
        tags = generate_tags(current_bottom)
        bottoms.append({"text": current_bottom.strip(), "tokens": current_tokens, "tags": tags})

    # Mid-Level: Summarize Bottoms (~5k tokens each)
    mids = []
    for i in range(0, len(bottoms), 2):  # Pair bottoms for ~10k input
        input_text = "\n".join(bottom["text"] for bottom in bottoms[i:i+2])
        summary = summarize(input_text, CHUNK_SIZES["mid"])
        tags = generate_tags(summary)
        mids.append({"text": summary, "tokens": estimate_tokens(summary), "tags": tags, "bottom_ids": [i, i+1]})

    # Top-Level: Summarize Mids (~1k tokens)
    top_input = "\n".join(mid["text"] for mid in mids)
    top_summary = summarize(top_input, CHUNK_SIZES["top"])
    top_tags = generate_tags(top_summary)
    top = {"text": top_summary, "tokens": estimate_tokens(top_summary), "tags": top_tags, "mid_ids": list(range(len(mids)))}

    return {"top": top, "mids": mids, "bottoms": bottoms}

# Execute and Save
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

chunks = chunk_data(conversations)
for level, data_list in [("top", [chunks["top"]]), ("mid", chunks["mids"]), ("bottom", chunks["bottoms"])]:
    for i, chunk in enumerate(data_list):
        with open(f"{OUTPUT_DIR}/claudia_{level}_{i+1}.json", "w", encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)

print(f"Chunked files saved in {OUTPUT_DIR}. Review and adjust as needed.")
