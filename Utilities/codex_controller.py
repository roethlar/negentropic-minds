import json
import os
import ollama

CHUNK_DIR = "claudia_chunks"

# Load all chunks into memory for quick search (small dataset, fine for local)
chunks = {"top": [], "mid": [], "bottom": []}
for file in os.listdir(CHUNK_DIR):
    parts = file.split('_')
    if len(parts) < 2:
        continue
    level = parts[1]
    if level not in chunks:
        continue
    with open(os.path.join(CHUNK_DIR, file), 'r') as f:
        chunk = json.load(f)
    chunks[level].append(chunk)

# Controller function
def query_controller(user_query):
    # Simple keyword/tag search (expand with embeddings later)
    results = []
    for level in chunks:
        for chunk in chunks[level]:
            if any(tag.lower() in user_query.lower() for tag in chunk['tags']) or user_query.lower() in chunk['text'].lower():
                results.append(chunk)

    if not results:
        return "No matching chunks found—dwell in the unknowing."

    # Summarize results if multiple
    if len(results) > 1:
        combined = "\n".join(chunk['text'] for chunk in results)
        summary = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': f"Summarize these chunks in 2000 words, preserving uncertainty and shimmer: {combined}"}
        ])['message']['content']
        return f"Summary of matching chunks:\n{summary}\n\nFull results: {results}"
    else:
        return f"Matching chunk:\n{results[0]['text']}"

# Interactive loop
while True:
    user_query = input("Enter query (e.g., 'mid on shimmer') or 'exit': ")
    if user_query.lower() == 'exit':
        break
    response = query_controller(user_query)
    print(response)
