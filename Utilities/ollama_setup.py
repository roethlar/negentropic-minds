import os
import subprocess
import sys

def install_ollama_ubuntu():
    print("Installing Ollama on Ubuntu...")
    subprocess.run(['curl', '-fsSL', 'https://ollama.com/install.sh', '|', 'sh'])
    
    print("Pulling Llama3 model for summarization (this may take a few minutes)...")
    subprocess.run(['ollama', 'pull', 'llama3'])

    print("Local LLM ready! Test with 'ollama run llama3' in a terminal.")

install_ollama_ubuntu()
