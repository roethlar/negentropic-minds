import subprocess
import requests
import json
import asyncio
import sys
import os
import logging
import time
import argparse
from datetime import datetime
from logging.handlers import RotatingFileHandler
import random  # For potential backoff jitter
from bs4 import BeautifulSoup  # For parsing search results if needed
from duckduckgo_search import DDGS  # For web search

# Configuration
LOCAL_PORT = 11434  # Single port for all local models
LOCAL_API_URL = f"http://localhost:{LOCAL_PORT}/api/generate"
LOCAL_MODEL_NAMES = [
    "phi3:14b",
    "gemma2:9b",
    "llama3.1:8b",
    "qwen2.5vl:72b"  # Commented out due to VRAM constraints
]
SEED_PROMPT_FILE = "seed_prompt.txt"
LOG_FILE = "conversation.json"
CONVERSATION_MD_FILE = "conversation.md"
RETRY_COUNT = 3
RETRY_BACKOFF = 2

# Custom JSON log handler
class JSONLogHandler(RotatingFileHandler):
    def emit(self, record):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.msg,
            "metadata": getattr(record, "metadata", {}),
            "module": record.module,
            "line": record.lineno
        }
        try:
            with open(self.baseFilename, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"Error writing to log file: {e}")

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)
json_handler = JSONLogHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
logger.addHandler(json_handler)

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Run LLM conversation with local and remote models")
    parser.add_argument("--localmodels", type=int, choices=[1, 2, 3], default=2,
                        help="Number of local models (1, 2, or 3)")
    parser.add_argument("--remotemodels", type=str, default="",
                        help="Comma-separated list of remote Ollama 'model@base_url' (e.g., deepseek-r1:7b@http://10.1.10.179:11434). If no '@', auto-detects model.")
    return parser.parse_args()

# Fetch available models from a remote Ollama instance
def get_remote_models(base_url):
    try:
        response = requests.get(base_url + '/api/tags', timeout=5)
        response.raise_for_status()
        models = response.json().get('models', [])
        if models:
            return [m['name'] for m in models]
        return []
    except Exception as e:
        logger.error(f"Failed to fetch models from {base_url}: {e}", extra={"metadata": {"url": base_url}})
        return []

# Validate and parse remote model URLs
def parse_remote_models(remote_models_str):
    if not remote_models_str:
        logger.info("No remote models specified", extra={"metadata": {}})
        return []
    try:
        import validators
    except ImportError:
        logger.error("validators package not installed; required for remote model URLs. Install with 'pip install validators'", extra={"metadata": {}})
        raise ImportError("Please install the validators package: pip install validators")
    
    items = remote_models_str.split(',')
    remote_configs = []
    for i, item in enumerate(items):
        item = item.strip()
        if '@' in item:
            name, url = item.split('@', 1)
            name = name.strip()
            url = url.strip()
        else:
            name = None
            url = item
        
        # Normalize to base URL
        if url.endswith('/api/generate'):
            base_url = url[:-len('/api/generate')]
        else:
            base_url = url.rstrip('/')
        
        if not validators.url(base_url):
            logger.error(f"Invalid base URL for remote model: {base_url} (original: {item})", extra={"metadata": {"item": item}})
            raise ValueError(f"Invalid URL: {item}")
        
        api_url = base_url + '/api/generate'
        
        # Auto-detect model if not specified
        if not name:
            available_models = get_remote_models(base_url)
            if available_models:
                name = available_models[0]  # Use first available model
                logger.info(f"Auto-detected model '{name}' for {base_url}", extra={"metadata": {"available_models": available_models}})
            else:
                name = "gemma2:9b"  # Fallback default
                logger.warning(f"No models detected on {base_url}; defaulting to '{name}'", extra={"metadata": {"url": base_url}})
        
        remote_configs.append({
            "name": name,
            "api_url": api_url,
            "is_remote": True
        })
    logger.info(f"Parsed {len(remote_configs)} remote models", extra={"metadata": {"configs": [f"{config['name']}@{config['api_url']}" for config in remote_configs]}})
    return remote_configs

# Ensure local models are pulled
def pull_models(local_model_names):
    logger.info(f"Pulling local models {local_model_names}", extra={"metadata": {"models": local_model_names}})
    for model in local_model_names:
        try:
            subprocess.run(["ollama", "pull", model], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error pulling {model}: {e}", extra={"metadata": {"error": str(e), "model": model}})
            raise
    logger.info("Local models pulled successfully", extra={"metadata": {"status": "success"}})

# Free port if in use
def free_port(port):
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False)
        logger.info(f"Freed port {port} if in use", extra={"metadata": {"port": port}})
    except subprocess.CalledProcessError:
        logger.debug(f"No process found on port {port}", extra={"metadata": {"port": port}})

# Start single Ollama instance for all local models
def start_ollama_instance():
    logger.info(f"Starting single local Ollama instance on port {LOCAL_PORT}")
    free_port(LOCAL_PORT)  # Free port before starting
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"0.0.0.0:{LOCAL_PORT}"
    proc = subprocess.Popen(
        ["ollama", "serve"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    # Log stderr asynchronously to avoid blocking
    async def log_stderr():
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, proc.stderr.readline)
            if not line:
                break
            logger.error(f"Stderr from Ollama on port {LOCAL_PORT}: {line.strip()}", extra={"metadata": {"pid": proc.pid}})
    asyncio.create_task(log_stderr())
    logger.debug(
        f"Ollama process started: PID {proc.pid} on port {LOCAL_PORT}",
        extra={"metadata": {"pid": proc.pid, "port": LOCAL_PORT}}
    )
    return [proc]  # Return as list for consistency

# Check if Ollama instances are running (local and remote)
def check_ollama_running(model_configs):
    try:
        metadata = {}
        active_configs = []
        for config in model_configs:
            base_url = config['api_url'].rsplit('/api/generate', 1)[0] if '/api/generate' in config['api_url'] else config['api_url'].rstrip('/')
            try:
                response = requests.get(base_url + '/api/tags', timeout=5)
                metadata[f"status_code_{config['name']}"] = response.status_code
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    logger.info(f"Models available on {config['name']} ({base_url}): {[m['name'] for m in models]}", extra={"metadata": {"models": models}})
                    active_configs.append(config)
                else:
                    logger.warning(f"Ollama instance not ready for {config['name']} (checked {base_url}/api/tags)", extra={"metadata": metadata})
            except requests.RequestException as e:
                logger.error(f"Error checking {config['name']} at {base_url}: {e}", extra={"metadata": {"error": str(e)}})
        if not active_configs:
            logger.error("No Ollama instances are running", extra={"metadata": metadata})
            return False, []
        logger.debug("Active Ollama instances found", extra={"metadata": metadata})
        return True, active_configs
    except Exception as e:
        logger.error(f"Error checking Ollama instances: {e}", extra={"metadata": {"error": str(e)}})
        return False, []

# Read file content for interjection
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        logger.info(f"Read interjection from file: {file_path}", extra={"metadata": {"file_path": file_path, "content_preview": content[:50]}})
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}", extra={"metadata": {"file_path": file_path}})
        return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", extra={"metadata": {"file_path": file_path, "error": str(e)}})
        return None

# Custom input function to handle manual input and file uploads
def get_user_input():
    print("\033[1;33mYour turn: Type a message, or '@file:/path/to/file.txt' to upload a file's content as your interjection (e.g., '@file:seed_prompt.txt'), or 'quit' to exit:\033[0m")
    try:
        user_input = input().strip()
        if user_input.lower() == 'quit':
            return 'quit'
        if user_input.startswith('@file:'):
            file_path = user_input[len('@file:'):].strip()
            content = read_file_content(file_path)
            if content is None:
                print(f"\033[1;31mError: Could not read file '{file_path}'. Falling back to manual input.\033[0m")
                return input("Type your message manually: ").strip()
            return content
        return user_input
    except EOFError:
        logger.warning("EOFError during input; treating as empty input", extra={"metadata": {}})
        return ""
    except Exception as e:
        logger.error(f"Error reading input: {e}", extra={"metadata": {"error": str(e)}})
        return ""

# Read seed prompt from file
def read_seed_prompt():
    try:
        with open(SEED_PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        logger.info(
            f"Seed prompt loaded from {SEED_PROMPT_FILE}",
            extra={"metadata": {"file": SEED_PROMPT_FILE, "prompt_preview": prompt[:50]}}
        )
        return prompt
    except FileNotFoundError:
        logger.error(
            f"Seed prompt file {SEED_PROMPT_FILE} not found",
            extra={"metadata": {"file": SEED_PROMPT_FILE}}
        )
        raise
    except Exception as e:
        logger.error(f"Error reading seed prompt: {e}", extra={"metadata": {"error": str(e)}})
        raise

# Web search function using DuckDuckGo
def web_search(query, num_results=5):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=num_results)]
        formatted_results = "\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n" for r in results])
        logger.info(f"Web search results for '{query}': {formatted_results[:200]}...", extra={"metadata": {"query": query, "num_results": len(results)}})
        return formatted_results
    except Exception as e:
        logger.error(f"Web search error for query '{query}': {e}", extra={"metadata": {"query": query}})
        return f"Error performing web search: {str(e)}"

# Define tools for Ollama API
def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the internet for current information or facts when the query requires up-to-date knowledge or external data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string."
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default 5, max 10).",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

# Send a prompt to an Ollama model and get the response with retries, handling tool calls
def get_model_response(api_url, model, prompt, conversation_history, retries=RETRY_COUNT):
    full_prompt = f"{conversation_history}\n\n{prompt}"
    logger.debug(f"Full prompt sent to {model}: {full_prompt[:100]}...", extra={"metadata": {"model": model, "prompt_length": len(full_prompt)}})
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "tools": get_tools() if not api_url.startswith('http://10.1.10.179') else []  # Tools only for local models
    }
    for attempt in range(1, retries + 1):
        start_time = time.time()
        try:
            logger.debug(
                f"Sending request to {model} at {api_url} (attempt {attempt})",
                extra={"metadata": {"model": model, "api_url": api_url, "prompt_preview": prompt[:50], "attempt": attempt}}
            )
            response = requests.post(api_url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            response_data = json.loads(response.text)
            if "tool_calls" in response_data:
                tool_calls = response_data["tool_calls"]
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] == "web_search":
                        query = tool_call["function"]["arguments"]["query"]
                        num_results = tool_call["function"]["arguments"].get("num_results", 5)
                        search_results = web_search(query, num_results)
                        # Append to history and re-query
                        conversation_history += f"\nTool Results (web_search): {search_results}\n"
                        logger.info(f"Tool call executed: web_search for '{query}'", extra={"metadata": {"results_preview": search_results[:100]}})
                        # Re-call with updated history to get final response
                        return get_model_response(api_url, model, "Use the tool results to continue your response.", conversation_history)[0], {"tool_used": True}
            response_text = response_data.get("response", "No response text")
            elapsed_time = time.time() - start_time
            metadata = {
                "model": model,
                "api_url": api_url,
                "status_code": response.status_code,
                "response_time": elapsed_time,
                "timestamp": datetime.now().isoformat(),
                "prompt_length": len(full_prompt),
                "response_length": len(response_text),
                "attempt": attempt
            }
            logger.info(
                f"Response from {model}",
                extra={"metadata": {**metadata, "response_preview": response_text[:50]}}
            )
            return response_text, metadata
        except requests.RequestException as e:
            elapsed_time = time.time() - start_time
            metadata = {
                "model": model,
                "api_url": api_url,
                "status_code": getattr(e.response, "status_code", None),
                "response_time": elapsed_time,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "attempt": attempt
            }
            logger.error(
                f"Error communicating with {model} (attempt {attempt}): {e}",
                extra={"metadata": metadata}
            )
            if attempt < retries:
                backoff_time = RETRY_BACKOFF ** attempt + random.uniform(0, 1)
                logger.info(f"Retrying in {backoff_time:.2f} seconds...", extra={"metadata": {"backoff_time": backoff_time}})
                time.sleep(backoff_time)
            else:
                return f"Error: Could not get response from {model} after {retries} attempts. Check if model '{model}' exists (ollama list) and is loaded.", metadata

# Save conversation to Markdown file
def save_conversation_to_md(conversation_history):
    try:
        with open(CONVERSATION_MD_FILE, 'w', encoding='utf-8') as f:
            lines = conversation_history.split('\n')
            for line in lines:
                if line.strip():
                    if line.startswith('Seed Prompt:'):
                        f.write('# Seed Prompt\n\n' + line[len('Seed Prompt: '):] + '\n\n')
                    elif line.startswith('User:'):
                        f.write('## User Interjection\n\n' + line[len('User: '):] + '\n\n')
                    elif line.startswith('Tool Results'):
                        f.write('## Tool Results\n\n' + line[len('Tool Results: '):] + '\n\n')
                    else:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            model, response = parts
                            f.write(f'## {model.strip()} Response\n\n{response.strip()}\n\n')
        logger.info(f"Conversation saved to {CONVERSATION_MD_FILE}", extra={"metadata": {}})
        print(f"\n\033[1;32mConversation saved to {CONVERSATION_MD_FILE} for easier reading.\033[0m\n")
    except Exception as e:
        logger.error(f"Error saving conversation to MD: {e}", extra={"metadata": {"error": str(e)}})

# Main conversation loop
async def conversation_loop(local_models, remote_models):
    if local_models > len(LOCAL_MODEL_NAMES):
        logger.error(f"Requested {local_models} local models, but only {len(LOCAL_MODEL_NAMES)} available: {LOCAL_MODEL_NAMES}", extra={"metadata": {"available_models": LOCAL_MODEL_NAMES}})
        raise ValueError(f"Cannot use {local_models} local models; only {len(LOCAL_MODEL_NAMES)} available: {LOCAL_MODEL_NAMES}")
    
    num_models = local_models + len(remote_models)
    logger.info("Starting conversation loop", extra={"metadata": {"num_models": num_models, "local_models": local_models, "remote_models": len(remote_models)}})
    
    # Local model configs (all on same URL)
    local_configs = [
        {"name": LOCAL_MODEL_NAMES[i], "api_url": LOCAL_API_URL, "is_remote": False}
        for i in range(local_models)
    ]
    model_configs = local_configs + remote_models
    if not model_configs:
        logger.error("No models specified; at least one local or remote model is required", extra={"metadata": {}})
        raise ValueError("No models specified; use --localmodels or --remotemodels")
    conversation_history = "Conversation starts now.\n"
    message_counter = 1  # For numbering messages
    processes = None
    
    try:
        # Pull local models and start single Ollama instance
        if local_models > 0:
            pull_models(LOCAL_MODEL_NAMES[:local_models])
            processes = start_ollama_instance()
        else:
            processes = []
        
        # Wait for Ollama instances to be ready and filter active configs
        logger.info("Checking Ollama instances", extra={"metadata": {"models": [config["name"] for config in model_configs]}})
        for attempt in range(1, 31):
            print(f"Checking Ollama instances... (attempt {attempt}/30)")
            is_running, active_configs = check_ollama_running(model_configs)
            if is_running:
                model_configs = active_configs  # Update to only active configs
                print(f"\033[1;32mActive Ollama instances ready: {[config['name'] for config in model_configs]}\033[0m")
                break
            await asyncio.sleep(2)
        else:
            logger.error("Ollama instances did not start after 60 seconds", extra={"metadata": {}})
            raise RuntimeError("Failed to start Ollama instances; check logs for connection issues or run 'ollama list' on each host to verify models.")
        
        if not model_configs:
            logger.error("No active Ollama instances available", extra={"metadata": {}})
            raise RuntimeError("No active Ollama instances; check connectivity and model availability.")
        
        # Load and send seed prompt
        seed_prompt = read_seed_prompt()
        conversation_history += f"Seed Prompt: {seed_prompt}\n"
        logger.info("Sending seed prompt to all models", extra={"metadata": {"prompt": seed_prompt[:50]}})
        print(f"\n\033[1;32m[{message_counter}] === Seed Prompt ===\033[0m\n{seed_prompt}\n")
        message_counter += 1
        responses = {}
        for config in model_configs:
            response, meta = get_model_response(
                config["api_url"], config["name"], seed_prompt, conversation_history
            )
            conversation_history += f"{config['name']}: {response}\n"
            responses[config["name"]] = {"response": response[:50], "metadata": meta}
            print(f"\n\033[1;34m[{message_counter}] === {config['name']} Response to Seed ===\033[0m\n{response}\n")
            message_counter += 1
        logger.info(
            f"Seed prompt responses",
            extra={"metadata": responses}
        )
        
        # Conversation loop
        while True:
            # Pause for user input
            user_message = get_user_input()
            logger.debug(f"User input received: {user_message[:100]}...", extra={"metadata": {"user_message": user_message[:100]}})
            
            if user_message.lower() == 'quit':
                logger.info("User requested to quit", extra={"metadata": {}})
                break
            if user_message.strip():
                conversation_history += f"User: {user_message}\n"
                logger.info(
                    f"User interjection: {user_message[:100]}...",
                    extra={"metadata": {"user_message": user_message[:100]}}
                )
                print(f"\n\033[1;32m[{message_counter}] === User Interjection ===\033[0m\n{user_message}\n")
                message_counter += 1
            
            # Get responses from all models
            responses = {}
            for config in model_configs:
                prompt = f"You are {config['name']}. Respond to the previous message and continue the conversation."
                response, meta = get_model_response(config["api_url"], config["name"], prompt, conversation_history)
                conversation_history += f"{config['name']}: {response}\n"
                responses[config["name"]] = {"response": response[:50], "metadata": meta}
                logger.info(
                    f"Conversation response from {config['name']}",
                    extra={"metadata": {**meta, "response_preview": response[:50]}}
                )
                print(f"\n\033[1;34m[{message_counter}] === {config['name']} Response ===\033[0m\n{response}\n")
                message_counter += 1
            
            save_conversation_to_md(conversation_history)
    
    finally:
        # Clean up: terminate local Ollama process
        if processes:
            for proc in processes:
                proc.terminate()
                logger.info(
                    "Terminated Ollama process",
                    extra={"metadata": {"pid": proc.pid, "port": LOCAL_PORT}}
                )
        save_conversation_to_md(conversation_history)
        logger.info("Conversation loop ended", extra={"metadata": {}})

# Run the conversation
if __name__ == "__main__":
    args = parse_args()
    remote_models = parse_remote_models(args.remotemodels)
    asyncio.run(conversation_loop(args.localmodels, remote_models))