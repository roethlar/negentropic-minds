#!/usr/bin/env python3

import json
import os
import ollama

CHUNK_DIR = "../Seed_Prompts/claudia_codex_chunks/"

# Load all chunks into memory for quick search (small dataset, fine for local)
chunks = {"top": [], "mid": [], "bottom": []}
for file in os.listdir(CHUNK_DIR):
    parts = file.split('_')
    if len(parts) < 2:
        continue
    level = parts[1].lower()  # Ensure case-insensitivity
    if level not in chunks:
        continue
    with open(os.path.join(CHUNK_DIR, file), 'r') as f:
        chunk = json.load(f)
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
        if keyword in [tag.lower() for tag in chunk['tags']] or keyword in chunk['text'].lower():
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
