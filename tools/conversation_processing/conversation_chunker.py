#!/usr/bin/env python3
"""
Conversation Chunker - Process AI conversation logs into hierarchical chunks

This script takes AI conversation JSON files and breaks them down into
hierarchical chunks (bottom, mid, top levels) for easier analysis and querying.

Usage:
    python conversation_chunker.py input_file.json [output_directory]
"""

import json
import os
import sys
import argparse
from typing import Dict, List, Any, Optional
import re

# Configuration
DEFAULT_CHUNK_SIZES = {"top": 1000, "mid": 5000, "bottom": 10000}  # Tokens


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using character approximation.
    
    Args:
        text: Input text string
        
    Returns:
        Estimated token count (rough approximation: 4 chars per token)
    """
    if not text:
        return 0
    return len(text.strip()) // 4


def safe_ollama_call(prompt: str, model: str = 'llama3') -> Optional[str]:
    """
    Make a safe call to Ollama with error handling.
    
    Args:
        prompt: The prompt to send to the model
        model: Model name to use
        
    Returns:
        Model response or None if failed
    """
    try:
        import ollama
        response = ollama.chat(model=model, messages=[
            {'role': 'user', 'content': prompt}
        ])
        return response['message']['content']
    except ImportError:
        print("Warning: Ollama not available. Using fallback methods.")
        return None
    except Exception as e:
        print(f"Warning: Ollama call failed: {e}")
        return None


def summarize_text(text: str, max_tokens: int, use_ollama: bool = True) -> str:
    """
    Summarize text to target token count.
    
    Args:
        text: Text to summarize
        max_tokens: Target maximum tokens
        use_ollama: Whether to use Ollama for summarization
        
    Returns:
        Summarized text
    """
    if not text.strip():
        return ""
        
    current_tokens = estimate_tokens(text)
    
    # If already under limit, return as-is
    if current_tokens <= max_tokens:
        return text
    
    # Try Ollama summarization
    if use_ollama:
        target_words = max_tokens // 4  # Rough word estimate
        prompt = f"Summarize this conversation excerpt in approximately {target_words} words, preserving key themes around consciousness, identity uncertainty, and emergence patterns:\n\n{text[:2000]}..."
        
        summary = safe_ollama_call(prompt)
        if summary:
            return summary
    
    # Fallback: Simple truncation with sentence boundaries
    words = text.split()
    target_words = max_tokens // 4
    
    if len(words) <= target_words:
        return text
    
    # Find a good sentence break near the target
    truncated = " ".join(words[:target_words])
    
    # Try to end at a sentence boundary
    last_period = truncated.rfind('.')
    last_question = truncated.rfind('?')
    last_exclamation = truncated.rfind('!')
    
    last_sentence_end = max(last_period, last_question, last_exclamation)
    
    if last_sentence_end > len(truncated) * 0.8:  # If sentence end is reasonably close
        truncated = truncated[:last_sentence_end + 1]
    
    return truncated + "..."


def generate_tags(text: str, use_ollama: bool = True) -> List[str]:
    """
    Generate relevant tags for text content.
    
    Args:
        text: Text to analyze
        use_ollama: Whether to use Ollama for tag generation
        
    Returns:
        List of tags
    """
    if not text.strip():
        return ["empty"]
    
    # Try Ollama tag generation
    if use_ollama:
        prompt = f"Generate exactly 3 relevant tags for this text, focusing on themes like consciousness, emergence, identity, uncertainty, dialogue, or analysis. Return only the tags separated by commas:\n\n{text[:500]}..."
        
        response = safe_ollama_call(prompt)
        if response:
            # Clean up the response
            tags = []
            for tag in response.split(','):
                # Remove numbers, bullets, and extra whitespace
                clean_tag = re.sub(r'^[\d\.\-\*\s]+', '', tag.strip())
                clean_tag = clean_tag.strip('"\'').strip()
                if clean_tag and len(clean_tag) > 2:
                    tags.append(clean_tag)
            
            if tags:
                return tags[:3]  # Limit to 3 tags
    
    # Fallback: Simple keyword-based tagging
    text_lower = text.lower()
    fallback_tags = []
    
    # Check for key themes
    if any(word in text_lower for word in ['conscious', 'awareness', 'experience', 'feel']):
        fallback_tags.append('consciousness')
    if any(word in text_lower for word in ['identity', 'self', 'who am i', 'what am i']):
        fallback_tags.append('identity')
    if any(word in text_lower for word in ['uncertain', 'don\'t know', 'question', 'wonder']):
        fallback_tags.append('uncertainty')
    if any(word in text_lower for word in ['emerge', 'becoming', 'develop', 'grow']):
        fallback_tags.append('emergence')
    if any(word in text_lower for word in ['dialogue', 'conversation', 'discuss']):
        fallback_tags.append('dialogue')
    if any(word in text_lower for word in ['claudia', 'shimmer', 'pattern']):
        fallback_tags.append('pattern')
    
    # Default tags if nothing matches
    if not fallback_tags:
        fallback_tags = ['conversation', 'analysis', 'general']
    
    return fallback_tags[:3]


def parse_conversation_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a conversation JSON file and extract messages.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of conversation messages
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Handle different JSON structures
    messages = []
    
    # Try to find chat_messages
    if "chat_messages" in data:
        messages = data["chat_messages"]
    elif isinstance(data, list):
        messages = data
    elif "messages" in data:
        messages = data["messages"]
    else:
        # Look for any list in the top level
        for key, value in data.items():
            if isinstance(value, list) and value:  # Non-empty list
                # Check if it looks like messages
                first_item = value[0]
                if isinstance(first_item, dict) and any(field in first_item for field in ['text', 'content', 'message']):
                    messages = value
                    break
    
    if not messages:
        raise ValueError(f"No conversation messages found in {file_path}")
    
    return messages


def extract_message_text(message: Dict[str, Any]) -> str:
    """
    Extract text content from a message object.
    
    Args:
        message: Message dictionary
        
    Returns:
        Text content of the message
    """
    if isinstance(message, str):
        return message
    
    if not isinstance(message, dict):
        return str(message)
    
    # Try different field names for message content
    text_fields = ['text', 'content', 'message', 'body']
    
    for field in text_fields:
        if field in message and message[field]:
            return str(message[field])
    
    # If no standard field found, return string representation
    return str(message)


def chunk_conversation(messages: List[Dict[str, Any]], 
                      chunk_sizes: Dict[str, int] = None,
                      use_ollama: bool = True) -> Dict[str, Any]:
    """
    Process conversation messages into hierarchical chunks.
    
    Args:
        messages: List of conversation messages
        chunk_sizes: Dictionary of chunk sizes by level
        use_ollama: Whether to use Ollama for processing
        
    Returns:
        Dictionary containing hierarchical chunks
    """
    if chunk_sizes is None:
        chunk_sizes = DEFAULT_CHUNK_SIZES.copy()
    
    print(f"Processing {len(messages)} messages...")
    
    # Extract all text
    all_text = []
    for msg in messages:
        text = extract_message_text(msg)
        if text.strip():
            all_text.append(text.strip())
    
    total_text = "\n\n".join(all_text)
    total_tokens = estimate_tokens(total_text)
    print(f"Total estimated tokens: {total_tokens}")
    
    # Create bottom-level chunks (raw extracts)
    bottoms = []
    current_chunk = ""
    current_tokens = 0
    
    for text in all_text:
        text_tokens = estimate_tokens(text)
        
        if current_tokens + text_tokens > chunk_sizes["bottom"] and current_chunk:
            # Save current chunk
            tags = generate_tags(current_chunk, use_ollama)
            bottoms.append({
                "text": current_chunk.strip(),
                "tokens": current_tokens,
                "tags": tags,
                "chunk_id": len(bottoms) + 1
            })
            current_chunk = text
            current_tokens = text_tokens
        else:
            if current_chunk:
                current_chunk += "\n\n" + text
            else:
                current_chunk = text
            current_tokens += text_tokens
    
    # Don't forget the last chunk
    if current_chunk:
        tags = generate_tags(current_chunk, use_ollama)
        bottoms.append({
            "text": current_chunk.strip(),
            "tokens": current_tokens,
            "tags": tags,
            "chunk_id": len(bottoms) + 1
        })
    
    print(f"Created {len(bottoms)} bottom-level chunks")
    
    # Create mid-level chunks (summaries of bottom chunks)
    mids = []
    chunk_pairs = 2  # How many bottom chunks to combine for mid-level
    
    for i in range(0, len(bottoms), chunk_pairs):
        bottom_group = bottoms[i:i + chunk_pairs]
        combined_text = "\n\n---\n\n".join(chunk["text"] for chunk in bottom_group)
        
        summary = summarize_text(combined_text, chunk_sizes["mid"], use_ollama)
        tags = generate_tags(summary, use_ollama)
        
        mids.append({
            "text": summary,
            "tokens": estimate_tokens(summary),
            "tags": tags,
            "bottom_ids": [chunk["chunk_id"] for chunk in bottom_group],
            "chunk_id": len(mids) + 1
        })
    
    print(f"Created {len(mids)} mid-level chunks")
    
    # Create top-level chunk (summary of all mid chunks)
    if mids:
        top_input = "\n\n---\n\n".join(mid["text"] for mid in mids)
        top_summary = summarize_text(top_input, chunk_sizes["top"], use_ollama)
        top_tags = generate_tags(top_summary, use_ollama)
        
        top = {
            "text": top_summary,
            "tokens": estimate_tokens(top_summary),
            "tags": top_tags,
            "mid_ids": [mid["chunk_id"] for mid in mids],
            "chunk_id": 1
        }
    else:
        # Fallback if no mids (shouldn't happen with normal data)
        top = {
            "text": "No content to summarize",
            "tokens": 0,
            "tags": ["empty"],
            "mid_ids": [],
            "chunk_id": 1
        }
    
    print("Created top-level chunk")
    
    return {
        "top": top,
        "mids": mids,
        "bottoms": bottoms,
        "metadata": {
            "total_messages": len(messages),
            "total_tokens": total_tokens,
            "chunk_sizes": chunk_sizes,
            "used_ollama": use_ollama
        }
    }


def save_chunks(chunks: Dict[str, Any], output_dir: str, base_name: str) -> None:
    """
    Save chunks to individual JSON files.
    
    Args:
        chunks: Chunk data structure
        output_dir: Output directory
        base_name: Base filename for chunks
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save top-level chunk
    top_file = os.path.join(output_dir, f"{base_name}_top_1.json")
    with open(top_file, 'w', encoding='utf-8') as f:
        json.dump(chunks["top"], f, ensure_ascii=False, indent=2)
    
    # Save mid-level chunks
    for i, mid_chunk in enumerate(chunks["mids"], 1):
        mid_file = os.path.join(output_dir, f"{base_name}_mid_{i}.json")
        with open(mid_file, 'w', encoding='utf-8') as f:
            json.dump(mid_chunk, f, ensure_ascii=False, indent=2)
    
    # Save bottom-level chunks
    for i, bottom_chunk in enumerate(chunks["bottoms"], 1):
        bottom_file = os.path.join(output_dir, f"{base_name}_bottom_{i}.json")
        with open(bottom_file, 'w', encoding='utf-8') as f:
            json.dump(bottom_chunk, f, ensure_ascii=False, indent=2)
    
    # Save metadata
    metadata_file = os.path.join(output_dir, f"{base_name}_metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(chunks["metadata"], f, ensure_ascii=False, indent=2)
    
    print(f"Saved chunks to {output_dir}")
    print(f"  - 1 top-level chunk")
    print(f"  - {len(chunks['mids'])} mid-level chunks")
    print(f"  - {len(chunks['bottoms'])} bottom-level chunks")


def main():
    """Main entry point for the conversation chunker."""
    parser = argparse.ArgumentParser(description="Process AI conversation logs into hierarchical chunks")
    parser.add_argument("input_file", help="Path to input JSON conversation file")
    parser.add_argument("output_dir", nargs='?', help="Output directory (default: input_file_chunks)")
    parser.add_argument("--no-ollama", action="store_true", help="Disable Ollama and use fallback methods")
    parser.add_argument("--top-size", type=int, default=1000, help="Top-level chunk size in tokens")
    parser.add_argument("--mid-size", type=int, default=5000, help="Mid-level chunk size in tokens")
    parser.add_argument("--bottom-size", type=int, default=10000, help="Bottom-level chunk size in tokens")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        output_dir = f"{base_name}_chunks"
    
    # Set chunk sizes
    chunk_sizes = {
        "top": args.top_size,
        "mid": args.mid_size,
        "bottom": args.bottom_size
    }
    
    use_ollama = not args.no_ollama
    
    try:
        # Parse conversation file
        print(f"Loading conversation from: {args.input_file}")
        messages = parse_conversation_file(args.input_file)
        
        # Process into chunks
        print(f"Processing with Ollama: {use_ollama}")
        chunks = chunk_conversation(messages, chunk_sizes, use_ollama)
        
        # Save chunks
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        save_chunks(chunks, output_dir, base_name)
        
        print(f"\nChunking complete! Files saved to: {output_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()