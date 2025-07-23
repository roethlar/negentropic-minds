#!/usr/bin/env python3
"""
Batch Conversation Chunker - Process multiple AI conversation files into chunks

This script processes all JSON conversation files in a directory and creates
hierarchical chunks for each one.

Usage:
    python batch_chunker.py input_directory [output_directory]
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
import time

# Import the chunking functions from the main chunker
from conversation_chunker import (
    parse_conversation_file, 
    chunk_conversation, 
    save_chunks,
    DEFAULT_CHUNK_SIZES
)


def find_conversation_files(input_dir: str) -> List[str]:
    """
    Find all JSON files in the input directory and subdirectories.
    
    Args:
        input_dir: Directory to search
        
    Returns:
        List of JSON file paths
    """
    json_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Find all JSON files recursively
    for json_file in input_path.rglob("*.json"):
        if json_file.is_file():
            json_files.append(str(json_file))
    
    return sorted(json_files)


def process_batch(input_dir: str, 
                 output_dir: str, 
                 chunk_sizes: Dict[str, int] = None,
                 use_ollama: bool = True,
                 skip_existing: bool = False) -> Dict[str, Any]:
    """
    Process all conversation files in a directory.
    
    Args:
        input_dir: Input directory containing JSON files
        output_dir: Base output directory
        chunk_sizes: Chunk size configuration
        use_ollama: Whether to use Ollama for processing
        skip_existing: Whether to skip files that already have chunks
        
    Returns:
        Processing results and statistics
    """
    if chunk_sizes is None:
        chunk_sizes = DEFAULT_CHUNK_SIZES.copy()
    
    # Find all JSON files
    json_files = find_conversation_files(input_dir)
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return {"processed": 0, "errors": 0, "skipped": 0, "files": []}
    
    print(f"Found {len(json_files)} JSON files to process")
    
    results = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
        "files": [],
        "total_tokens": 0,
        "total_chunks": {"top": 0, "mid": 0, "bottom": 0}
    }
    
    # Create base output directory
    os.makedirs(output_dir, exist_ok=True)
    
    for i, file_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing: {os.path.basename(file_path)}")
        
        try:
            # Determine output subdirectory
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            file_output_dir = os.path.join(output_dir, f"{base_name}_chunks")
            
            # Check if already processed
            if skip_existing and os.path.exists(file_output_dir):
                metadata_file = os.path.join(file_output_dir, f"{base_name}_metadata.json")
                if os.path.exists(metadata_file):
                    print(f"  Skipping - already processed")
                    results["skipped"] += 1
                    continue
            
            # Parse and process the file
            start_time = time.time()
            messages = parse_conversation_file(file_path)
            chunks = chunk_conversation(messages, chunk_sizes, use_ollama)
            
            # Save chunks
            save_chunks(chunks, file_output_dir, base_name)
            
            # Update statistics
            processing_time = time.time() - start_time
            results["processed"] += 1
            results["total_tokens"] += chunks["metadata"]["total_tokens"]
            results["total_chunks"]["top"] += 1
            results["total_chunks"]["mid"] += len(chunks["mids"])
            results["total_chunks"]["bottom"] += len(chunks["bottoms"])
            
            file_info = {
                "file": file_path,
                "base_name": base_name,
                "output_dir": file_output_dir,
                "messages": len(messages),
                "tokens": chunks["metadata"]["total_tokens"],
                "chunks": {
                    "top": 1,
                    "mid": len(chunks["mids"]),
                    "bottom": len(chunks["bottoms"])
                },
                "processing_time": round(processing_time, 2)
            }
            results["files"].append(file_info)
            
            print(f"  ✓ Processed in {processing_time:.1f}s")
            print(f"    - {len(messages)} messages, {chunks['metadata']['total_tokens']} tokens")
            print(f"    - {len(chunks['bottoms'])} bottom, {len(chunks['mids'])} mid, 1 top chunk")
            
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}")
            results["errors"] += 1
            results["files"].append({
                "file": file_path,
                "error": str(e)
            })
    
    return results


def save_batch_manifest(results: Dict[str, Any], output_dir: str) -> None:
    """
    Save a manifest file with batch processing results.
    
    Args:
        results: Processing results
        output_dir: Output directory
    """
    manifest_path = os.path.join(output_dir, "batch_manifest.json")
    
    manifest = {
        "batch_summary": {
            "processed": results["processed"],
            "errors": results["errors"],
            "skipped": results["skipped"],
            "total_files": len(results["files"]),
            "total_tokens": results["total_tokens"],
            "total_chunks": results["total_chunks"]
        },
        "files": results["files"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\nBatch manifest saved to: {manifest_path}")


def main():
    """Main entry point for the batch conversation chunker."""
    parser = argparse.ArgumentParser(description="Process multiple AI conversation files into hierarchical chunks")
    parser.add_argument("input_dir", help="Directory containing JSON conversation files")
    parser.add_argument("output_dir", nargs='?', help="Output directory (default: input_dir_chunks)")
    parser.add_argument("--no-ollama", action="store_true", help="Disable Ollama and use fallback methods")
    parser.add_argument("--skip-existing", action="store_true", help="Skip files that already have chunks")
    parser.add_argument("--top-size", type=int, default=1000, help="Top-level chunk size in tokens")
    parser.add_argument("--mid-size", type=int, default=5000, help="Mid-level chunk size in tokens")
    parser.add_argument("--bottom-size", type=int, default=10000, help="Bottom-level chunk size in tokens")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found")
        sys.exit(1)
    
    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        input_name = os.path.basename(args.input_dir.rstrip('/'))
        output_dir = f"{input_name}_chunks"
    
    # Set chunk sizes
    chunk_sizes = {
        "top": args.top_size,
        "mid": args.mid_size,
        "bottom": args.bottom_size
    }
    
    use_ollama = not args.no_ollama
    
    try:
        print(f"Batch processing conversations from: {args.input_dir}")
        print(f"Output directory: {output_dir}")
        print(f"Using Ollama: {use_ollama}")
        print(f"Skip existing: {args.skip_existing}")
        print(f"Chunk sizes - Top: {chunk_sizes['top']}, Mid: {chunk_sizes['mid']}, Bottom: {chunk_sizes['bottom']}")
        
        # Process all files
        start_time = time.time()
        results = process_batch(
            args.input_dir, 
            output_dir, 
            chunk_sizes, 
            use_ollama, 
            args.skip_existing
        )
        total_time = time.time() - start_time
        
        # Save manifest
        save_batch_manifest(results, output_dir)
        
        # Print summary
        print(f"\n{'='*60}")
        print("BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total time: {total_time:.1f} seconds")
        print(f"Files processed: {results['processed']}")
        print(f"Files with errors: {results['errors']}")
        print(f"Files skipped: {results['skipped']}")
        print(f"Total tokens processed: {results['total_tokens']:,}")
        print(f"Total chunks created:")
        print(f"  - Top-level: {results['total_chunks']['top']}")
        print(f"  - Mid-level: {results['total_chunks']['mid']}")
        print(f"  - Bottom-level: {results['total_chunks']['bottom']}")
        
        if results['errors'] > 0:
            print(f"\nFiles with errors:")
            for file_info in results['files']:
                if 'error' in file_info:
                    print(f"  - {file_info['file']}: {file_info['error']}")
        
        print(f"\nAll output saved to: {output_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()