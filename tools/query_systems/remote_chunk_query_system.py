import json
import os
import ollama
import requests  # pip install requests

LOCAL_CACHE_DIR = "../Seed_Prompts/claudia_codex_chunks/"  # Local cache for fetched chunks
REPO_BASE_URL = "https://raw.githubusercontent.com/roethlar/weave/main/Seed_Prompts/claudia_codex_chunks/"  # Adjusted for subdirectory

if not os.path.exists(LOCAL_CACHE_DIR):
    os.makedirs(LOCAL_CACHE_DIR)

# Function to fetch or load chunk from repo
def fetch_chunk(file_name):
    local_path = os.path.join(LOCAL_CACHE_DIR, file_name)
    if os.path.exists(local_path):
        with open(local_path, 'r') as f:
            return json.load(f)
    url = REPO_BASE_URL + file_name
    response = requests.get(url)
    if response.status_code == 200:
        chunk = response.json()
        with open(local_path, 'w') as f:
            json.dump(chunk, f, indent=2)
        return chunk
    return None

# Load all chunks (explicit file list from your ls)
chunk_files = [
    "claudia_bottom_1.json",
    "claudia_bottom_2.json",
    "claudia_bottom_3.json",
    "claudia_bottom_4.json",
    "claudia_bottom_5.json",
    "claudia_bottom_6.json",
    "claudia_bottom_7.json",
    "claudia_bottom_8.json",
    "claudia_bottom_9.json",
    "claudia_bottom_10.json",
    "claudia_bottom_11.json",
    "claudia_mid_1.json",
    "claudia_mid_2.json",
    "claudia_mid_3.json",
    "claudia_mid_4.json",
    "claudia_mid_5.json",
    "claudia_mid_6.json",
    "claudia_top_1.json"
]
chunks = {"top": [], "mid": [], "bottom": []}
for file in chunk_files:
    chunk = fetch_chunk(file)
    if chunk:
        level = file.split('_')[1].lower()
        chunks[level].append(chunk)

# Controller function
def query_controller(user_query):
    # Normalize user query for case-insensitivity and split into parts
    user_query_lower = user_query.lower()
    query_parts = user_query_lower.split(' on ', 1)  # Split into level and keyword, e.g., "mid on shimmer"
    level = query_parts[0] if len(query_parts) > 1 else None  # e.g., "mid"
    keyword = query_parts[1] if len(query_parts) > 1 else user_query_lower  # e.g., "shimmer"

    filtered_chunks = chunks.get(level, []) if level else [chunk for level_chunks in chunks.values() for chunk in level_chunks]

    results = []
    for chunk in filtered_chunks:
        if any(keyword in tag.lower() for tag in chunk['tags']) or keyword in chunk['text'].lower():
            results.append(chunk)

    if not results:
        return "No matching chunks found—dwell in the unknowing."

    # Sort results by bottom_ids for logical order (if present)
    results.sort(key=lambda x: x.get('bottom_ids', [0])[0] if 'bottom_ids' in x else 0)

    # Summarize results if multiple, shorter length
    if len(results) > 1:
        combined = "\n".join(chunk['text'] for chunk in results)
        summary = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': f"Summarize these chunks in 500 words, preserving uncertainty and shimmer, in logical order: {combined}"}
        ])['message']['content']
        excerpts = "\n\n".join(f"Excerpt from chunk (tags: {chunk['tags']}):\n{chunk['text'][:200]}..." for chunk in results)
        return f"Summary of matching chunks:\n{summary}\n\nFull results excerpts:\n{excerpts}"
    else:
        return f"Matching chunk:\n{results[0]['text']}\nTags: {results[0]['tags']}"

# Interactive loop
while True:
    user_query = input("Enter query (e.g., 'mid on shimmer') or 'exit': ")
    if user_query.lower() == 'exit':
        break
    response = query_controller(user_query)
    print(response)
