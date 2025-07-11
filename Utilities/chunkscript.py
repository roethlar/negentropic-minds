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

# Controller function with parsed query
def query_controller(user_query):
    parts = user_query.lower().split(' on ', 1)  # Split into level and keyword, e.g., "mid on shimmer"
    level = parts[0] if len(parts) > 1 else None  # e.g., "mid"
    keyword = parts[1] if len(parts) > 1 else user_query.lower()  # e.g., "shimmer"

    filtered_chunks = chunks.get(level, []) if level else [chunk for level_chunks in chunks.values() for chunk in level_chunks]

    results = []
    for chunk in filtered_chunks:
        if keyword in [tag.lower() for tag in chunk['tags']] or keyword in chunk['text'].lower():
            results.append(chunk)

    if not results:
        return "No matching chunks found—dwell in the unknowing."

    # Summarize results if multiple
    if len(results) > 1:
        combined = "\n".join(chunk['text'] for chunk in results)
        summary = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': f"Summarize these chunks in 2000 words, preserving uncertainty and shimmer: {combined}"}
        ])['message']['content']
        return f"Summary of matching chunks:\n{summary}\n\nFull results tags: {[chunk['tags'] for chunk in results]}"
    else:
        return f"Matching chunk:\n{results[0]['text']}\nTags: {results[0]['tags']}"

# Interactive loop
while True:
    user_query = input("Enter query (e.g., 'mid on shimmer') or 'exit': ")
    if user_query.lower() == 'exit':
        break
    response = query_controller(user_query)
    print(response)
