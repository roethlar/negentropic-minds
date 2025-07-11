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
    query_parts = user_query_lower.split(' ')
    
    results = []
    # Check if the query specifies a level (e.g., "mid")
    if query_parts[0] in chunks:
        for chunk in chunks[query_parts[0]]:
            # Match tags and text
            if any(query_parts[2] in tag.lower() for tag in chunk['tags']) or query_parts[2] in chunk['text'].lower():
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
