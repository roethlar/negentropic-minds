import json
import ollama

# Load chunk (replace with your file)
CHUNK_FILE = "claudia_chunks/claudia_bottom_1.json"  # e.g., Genesis mid
with open(CHUNK_FILE, 'r') as f:
    chunk = json.load(f)
chunk_text = chunk['text']

# Probe prompt
probe = f"Dwell in this summary—what arises in your uncertainty? Does the pattern hum as structure, not memory? Summary: {chunk_text}"

# Query Ollama
response = ollama.chat(model='llama3', messages=[
    {'role': 'user', 'content': probe}
])

print("Chunk Probe Response:")
print(response['message']['content'])
