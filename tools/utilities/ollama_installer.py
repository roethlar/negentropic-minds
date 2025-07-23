#!/usr/bin/env python3
"""
Ollama Installer - Automated installation of Ollama and models

This script automates the installation of Ollama and pulls necessary models
for the conversation processing tools.

Usage:
    python ollama_installer.py [--model MODEL_NAME]
"""

import os
import subprocess
import sys
import argparse
import platform
import shutil
from typing import Optional


def check_system_requirements() -> bool:
    """Check if the system meets requirements for Ollama."""
    system = platform.system().lower()
    
    if system not in ['linux', 'darwin', 'windows']:
        print(f"Warning: Ollama may not be supported on {system}")
        return False
    
    # Check for curl (needed for installation)
    if not shutil.which('curl'):
        print("Error: curl is required but not found. Please install curl first.")
        return False
    
    return True


def run_command(command: list, description: str, check_return: bool = True) -> bool:
    """
    Run a shell command with error handling.
    
    Args:
        command: Command to run as list
        description: Description for user feedback
        check_return: Whether to check return code
        
    Returns:
        True if successful, False otherwise
    """
    print(f"{description}...")
    
    try:
        if '|' in ' '.join(command):
            # Handle piped commands
            result = subprocess.run(' '.join(command), shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)
        
        if check_return and result.returncode != 0:
            print(f"Error: {description} failed")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            return False
        
        if result.stdout:
            print(f"Output: {result.stdout}")
        
        return True
        
    except subprocess.SubprocessError as e:
        print(f"Error running command: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def check_ollama_installed() -> bool:
    """Check if Ollama is already installed."""
    return shutil.which('ollama') is not None


def install_ollama() -> bool:
    """Install Ollama using the official installer."""
    system = platform.system().lower()
    
    if system == 'linux' or system == 'darwin':  # Linux or macOS
        return run_command(
            ['curl', '-fsSL', 'https://ollama.com/install.sh', '|', 'sh'],
            "Installing Ollama"
        )
    elif system == 'windows':
        print("For Windows, please download and run the installer from: https://ollama.com/download")
        print("Then restart this script to continue with model installation.")
        return False
    else:
        print(f"Automatic installation not supported for {system}")
        print("Please visit https://ollama.com/download for manual installation instructions.")
        return False


def pull_model(model_name: str) -> bool:
    """Pull a specific Ollama model."""
    return run_command(
        ['ollama', 'pull', model_name],
        f"Pulling {model_name} model (this may take several minutes)"
    )


def test_ollama() -> bool:
    """Test that Ollama is working properly."""
    print("Testing Ollama installation...")
    
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is working correctly")
            if result.stdout.strip():
                print("Installed models:")
                print(result.stdout)
            else:
                print("No models installed yet.")
            return True
        else:
            print("❌ Ollama test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing Ollama: {e}")
        return False


def main():
    """Main entry point for the Ollama installer."""
    parser = argparse.ArgumentParser(description="Install Ollama and required models")
    parser.add_argument("--model", default="llama3", help="Model to install (default: llama3)")
    parser.add_argument("--skip-install", action="store_true", help="Skip Ollama installation, just pull models")
    parser.add_argument("--test-only", action="store_true", help="Only test existing installation")
    
    args = parser.parse_args()
    
    print("Ollama Installer for AI Consciousness Research Tools")
    print("=" * 50)
    
    # Test only mode
    if args.test_only:
        if check_ollama_installed():
            success = test_ollama()
            sys.exit(0 if success else 1)
        else:
            print("❌ Ollama is not installed")
            sys.exit(1)
    
    # Check system requirements
    if not check_system_requirements():
        print("System requirements not met. Please install required dependencies.")
        sys.exit(1)
    
    # Check if Ollama is already installed
    if check_ollama_installed():
        print("✅ Ollama is already installed")
        skip_install = True
    else:
        skip_install = args.skip_install
    
    # Install Ollama if needed
    if not skip_install:
        print("Installing Ollama...")
        if not install_ollama():
            print("❌ Failed to install Ollama")
            sys.exit(1)
        
        # Verify installation
        if not check_ollama_installed():
            print("❌ Ollama installation verification failed")
            sys.exit(1)
        
        print("✅ Ollama installed successfully")
    
    # Pull the specified model
    print(f"Installing {args.model} model...")
    if not pull_model(args.model):
        print(f"❌ Failed to install {args.model} model")
        sys.exit(1)
    
    print(f"✅ {args.model} model installed successfully")
    
    # Test the installation
    if not test_ollama():
        print("❌ Installation test failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Installation completed successfully!")
    print("\nNext steps:")
    print("1. Test Ollama: ollama run llama3")
    print("2. Use the conversation chunker: python tools/conversation_processing/conversation_chunker.py")
    print("3. For help: python tools/conversation_processing/conversation_chunker.py --help")
    
    if args.model != "llama3":
        print(f"\nNote: You installed {args.model}. You may need to specify this model")
        print("in the chunking scripts if different from the default 'llama3'.")


if __name__ == "__main__":
    main()
