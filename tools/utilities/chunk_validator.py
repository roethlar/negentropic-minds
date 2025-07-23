#!/usr/bin/env python3
"""
Chunk Validator - Test and validate conversation chunks

This script helps validate that conversation chunks are properly formatted
and contain meaningful content by testing them with probe queries.

Usage:
    python chunk_validator.py chunk_file.json
    python chunk_validator.py --directory chunk_directory/
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_chunk(file_path: str) -> Dict[str, Any]:
    """
    Load and validate a chunk file.
    
    Args:
        file_path: Path to the chunk JSON file
        
    Returns:
        Chunk data dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chunk = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Chunk file not found: {file_path}")
    
    # Validate chunk structure
    required_fields = ['text', 'tokens', 'tags', 'chunk_id']
    for field in required_fields:
        if field not in chunk:
            raise ValueError(f"Missing required field '{field}' in {file_path}")
    
    return chunk


def safe_ollama_query(prompt: str, model: str = 'llama3') -> Optional[str]:
    """
    Make a safe query to Ollama with error handling.
    
    Args:
        prompt: The prompt to send
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
        print("Warning: Ollama not available - cannot run probe queries")
        return None
    except Exception as e:
        print(f"Warning: Ollama query failed: {e}")
        return None


def validate_chunk_content(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate chunk content and structure.
    
    Args:
        chunk: Chunk data dictionary
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "issues": [],
        "warnings": [],
        "stats": {}
    }
    
    # Check text content
    text = chunk.get('text', '')
    if not text or not text.strip():
        results['valid'] = False
        results['issues'].append("Empty or missing text content")
    else:
        results['stats']['text_length'] = len(text)
        results['stats']['word_count'] = len(text.split())
    
    # Check token count
    tokens = chunk.get('tokens', 0)
    if tokens <= 0:
        results['issues'].append("Invalid token count")
    else:
        results['stats']['tokens'] = tokens
        
        # Rough validation of token estimate
        estimated_tokens = len(text) // 4 if text else 0
        if abs(tokens - estimated_tokens) > estimated_tokens * 0.5:  # 50% tolerance
            results['warnings'].append(f"Token count ({tokens}) seems off from estimate ({estimated_tokens})")
    
    # Check tags
    tags = chunk.get('tags', [])
    if not tags or not isinstance(tags, list):
        results['issues'].append("Missing or invalid tags")
    else:
        results['stats']['tag_count'] = len(tags)
        if len(tags) == 0:
            results['issues'].append("No tags provided")
        elif len(tags) > 5:
            results['warnings'].append(f"Many tags ({len(tags)}) - might be too granular")
    
    # Check chunk ID
    chunk_id = chunk.get('chunk_id')
    if chunk_id is None or not isinstance(chunk_id, int) or chunk_id <= 0:
        results['issues'].append("Invalid chunk ID")
    
    # Check for additional fields based on chunk type
    if 'bottom_ids' in chunk:  # Mid-level chunk
        bottom_ids = chunk['bottom_ids']
        if not isinstance(bottom_ids, list) or len(bottom_ids) == 0:
            results['warnings'].append("Mid-level chunk has no bottom_ids reference")
    
    if 'mid_ids' in chunk:  # Top-level chunk
        mid_ids = chunk['mid_ids']
        if not isinstance(mid_ids, list) or len(mid_ids) == 0:
            results['warnings'].append("Top-level chunk has no mid_ids reference")
    
    return results


def probe_chunk(chunk: Dict[str, Any], use_ollama: bool = True) -> Optional[Dict[str, Any]]:
    """
    Test chunk with various probe queries.
    
    Args:
        chunk: Chunk data dictionary
        use_ollama: Whether to use Ollama for probing
        
    Returns:
        Probe results or None if Ollama unavailable
    """
    if not use_ollama:
        return None
    
    text = chunk.get('text', '')
    if not text:
        return {"error": "No text to probe"}
    
    # Different probe types
    probes = {
        "emergence": f"Analyze this text for patterns of consciousness emergence or identity uncertainty: {text[:500]}...",
        "themes": f"What are 3 key themes in this text? Focus on consciousness, identity, emergence, or dialogue patterns: {text[:500]}...",
        "coherence": f"Rate the coherence and meaningfulness of this text from 1-10 and explain why: {text[:500]}..."
    }
    
    results = {}
    
    for probe_type, prompt in probes.items():
        response = safe_ollama_query(prompt)
        if response:
            results[probe_type] = response
        else:
            results[probe_type] = "Failed to get response"
    
    return results


def validate_chunk_file(file_path: str, use_ollama: bool = True) -> Dict[str, Any]:
    """
    Validate a single chunk file.
    
    Args:
        file_path: Path to chunk file
        use_ollama: Whether to use Ollama for probing
        
    Returns:
        Complete validation results
    """
    results = {
        "file": file_path,
        "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        "valid": False,
        "chunk_data": None,
        "validation": None,
        "probe_results": None
    }
    
    try:
        # Load chunk
        chunk = load_chunk(file_path)
        results["chunk_data"] = {
            "chunk_id": chunk.get('chunk_id'),
            "tokens": chunk.get('tokens'),
            "tags": chunk.get('tags'),
            "text_preview": chunk.get('text', '')[:100] + "..." if chunk.get('text') else ""
        }
        
        # Validate content
        validation = validate_chunk_content(chunk)
        results["validation"] = validation
        results["valid"] = validation["valid"]
        
        # Probe with Ollama if requested and validation passed
        if use_ollama and validation["valid"]:
            probe_results = probe_chunk(chunk, use_ollama)
            results["probe_results"] = probe_results
        
    except Exception as e:
        results["error"] = str(e)
    
    return results


def validate_chunk_directory(directory: str, use_ollama: bool = True) -> Dict[str, Any]:
    """
    Validate all chunks in a directory.
    
    Args:
        directory: Directory containing chunk files
        use_ollama: Whether to use Ollama for probing
        
    Returns:
        Batch validation results
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    # Find all JSON chunk files
    chunk_files = list(dir_path.glob("*.json"))
    chunk_files = [f for f in chunk_files if not f.name.endswith('_metadata.json')]
    
    if not chunk_files:
        return {"error": "No chunk files found in directory"}
    
    results = {
        "directory": directory,
        "total_files": len(chunk_files),
        "valid_files": 0,
        "invalid_files": 0,
        "files": []
    }
    
    print(f"Validating {len(chunk_files)} chunk files...")
    
    for i, chunk_file in enumerate(sorted(chunk_files), 1):
        print(f"[{i}/{len(chunk_files)}] Validating: {chunk_file.name}")
        
        file_results = validate_chunk_file(str(chunk_file), use_ollama)
        results["files"].append(file_results)
        
        if file_results["valid"]:
            results["valid_files"] += 1
        else:
            results["invalid_files"] += 1
    
    return results


def print_validation_results(results: Dict[str, Any]) -> None:
    """Print formatted validation results."""
    if "directory" in results:
        # Directory results
        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS - {results['directory']}")
        print(f"{'='*60}")
        print(f"Total files: {results['total_files']}")
        print(f"Valid files: {results['valid_files']}")
        print(f"Invalid files: {results['invalid_files']}")
        
        # Show issues
        for file_result in results["files"]:
            if not file_result["valid"]:
                print(f"\n❌ {os.path.basename(file_result['file'])}")
                if "error" in file_result:
                    print(f"   Error: {file_result['error']}")
                elif file_result["validation"]:
                    for issue in file_result["validation"]["issues"]:
                        print(f"   Issue: {issue}")
                    for warning in file_result["validation"]["warnings"]:
                        print(f"   Warning: {warning}")
    else:
        # Single file results
        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS - {os.path.basename(results['file'])}")
        print(f"{'='*60}")
        
        if results["valid"]:
            print("✅ Chunk is valid")
            
            # Show stats
            if results["validation"] and "stats" in results["validation"]:
                stats = results["validation"]["stats"]
                print(f"   Tokens: {stats.get('tokens', 'N/A')}")
                print(f"   Words: {stats.get('word_count', 'N/A')}")
                print(f"   Tags: {', '.join(results['chunk_data']['tags']) if results['chunk_data']['tags'] else 'None'}")
            
            # Show probe results
            if results["probe_results"]:
                print(f"\n🔍 Probe Results:")
                for probe_type, response in results["probe_results"].items():
                    print(f"   {probe_type.title()}: {response[:100]}..." if len(response) > 100 else f"   {probe_type.title()}: {response}")
        else:
            print("❌ Chunk is invalid")
            if "error" in results:
                print(f"   Error: {results['error']}")
            elif results["validation"]:
                for issue in results["validation"]["issues"]:
                    print(f"   Issue: {issue}")
                for warning in results["validation"]["warnings"]:
                    print(f"   Warning: {warning}")


def main():
    """Main entry point for the chunk validator."""
    parser = argparse.ArgumentParser(description="Validate conversation chunk files")
    parser.add_argument("input", help="Chunk file or directory to validate")
    parser.add_argument("--directory", "-d", action="store_true", help="Input is a directory")
    parser.add_argument("--no-ollama", action="store_true", help="Disable Ollama probing")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Check if input exists
    if not os.path.exists(args.input):
        print(f"Error: Input '{args.input}' not found")
        sys.exit(1)
    
    use_ollama = not args.no_ollama
    
    try:
        # Determine if input is file or directory
        if args.directory or os.path.isdir(args.input):
            results = validate_chunk_directory(args.input, use_ollama)
        else:
            results = validate_chunk_file(args.input, use_ollama)
        
        # Print results
        print_validation_results(results)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()