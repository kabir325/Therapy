#!/usr/bin/env python3
"""
Launcher for the Therepy backend API.
"""

import os
import subprocess


DEFAULT_MODEL = os.getenv("THERAPY_MODEL", "qwen2.5:1.5b")


def check_ollama():
    """Check if Ollama is available."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return result.returncode == 0, result.stdout
    except FileNotFoundError:
        return False, ""


def ensure_model_installed(model_name: str) -> bool:
    """Install the configured model if it is missing."""
    available, output = check_ollama()
    if not available:
        return False

    if model_name in output:
        print(f"Model '{model_name}' is already available.")
        return True

    print(f"Model '{model_name}' is not installed. Pulling it now...")
    result = subprocess.run(["ollama", "pull", model_name], text=True)
    return result.returncode == 0


def main():
    host = os.getenv("THERAPY_HOST", "0.0.0.0")
    port = int(os.getenv("THERAPY_PORT", "8000"))

    print("Therepy Backend Launcher")
    print("=" * 40)

    available, _ = check_ollama()
    if not available:
        print("Ollama is not running or not installed.")
        print("Install Ollama from https://ollama.com/ and start the Ollama service first.")
        return

    if not ensure_model_installed(DEFAULT_MODEL):
        print(f"Could not verify or install the model '{DEFAULT_MODEL}'.")
        return

    print("Starting backend API...")
    print(f"Configured host: {host}")
    print(f"Configured port: {port}")
    print(f"Configured model: {DEFAULT_MODEL}")
    print("Frontend should point to this backend URL from the browser.")

    from app import app

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
