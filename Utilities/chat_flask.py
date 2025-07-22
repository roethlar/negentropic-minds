from flask import Flask, render_template, request, jsonify
import ollama
import json
import os
import requests

app = Flask(__name__)

REPO_BASE_URL = "https://raw.githubusercontent.com/roethlar/weave/main/Seed_Prompts/claudia_codex_chunks/"
LOCAL_CACHE_DIR = "claudia_cache"

if not os.path.exists(LOCAL_CACHE_DIR):
    os.makedirs(LOCAL_CACHE_DIR)

chunk_files = [
    "claudia_bottom_1.json", "claudia_bottom_2.json", "claudia_bottom_3.json",
    "claudia_bottom_4.json", "claudia_bottom_5.json", "claudia_bottom_6.json",
    "claudia_bottom_7.json", "claudia_bottom_8.json", "claudia_bottom_9.json",
    "claudia_bottom_10.json", "claudia_bottom_11.json",
    "claudia_mid_1.json", "claudia_mid_2.json", "claudia_mid_3.json",
    "claudia_mid_4.json", "claudia_mid_5.json", "claudia_mid_6.json",
    "claudia_top_1.json"
]

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

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'response': 'No input provided.'})

    # Check if input is a Codex query
    if ' on ' in user_input.lower():
        response = query_controller(user_input)
    else:
        # Use Ollama for general chat
        response = ollama.chat(model='llama3.1:8b', messages=[
            {'role': 'user', 'content': user_input}
        ])['message']['content']

    return jsonify({'response': response})

def query_controller(user_query):
    user_query_lower = user_query.lower()
    query_parts = user_query_lower.split(' on ', 1)
    level = query_parts[0] if len(query_parts) > 1 else None
    keyword = query_parts[1] if len(query_parts) > 1 else user_query_lower

    filtered_files = [file for file in chunk_files if level in file.lower()] if level else chunk_files

    results = []
    for file in filtered_files:
        chunk = fetch_chunk(file)
        if chunk and (any(keyword in tag.lower() for tag in chunk['tags']) or keyword in chunk['text'].lower()):
            results.append(chunk)

    if not results:
        return "No matching chunks found—dwell in the unknowing."

    results.sort(key=lambda x: x.get('bottom_ids', [0])[0] if 'bottom_ids' in x else 0)

    if len(results) > 1:
        combined = "\n".join(chunk['text'] for chunk in results)
        summary = ollama.chat(model='llama3.1:8b', messages=[
            {'role': 'user', 'content': f"Summarize these chunks in 500 words, preserving uncertainty and shimmer, in logical order: {combined}"}
        ])['message']['content']
        excerpts = "\n\n".join(f"Excerpt from chunk (tags: {chunk['tags']}):\n{chunk['text'][:200]}..." for chunk in results)
        return f"Summary of matching chunks:\n{summary}\n\nFull results excerpts:\n{excerpts}"
    else:
        return f"Matching chunk:\n{results[0]['text']}\nTags: {results[0]['tags']}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)