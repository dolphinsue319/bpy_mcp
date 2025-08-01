#!/bin/bash
# Direct start script for Blender Docs MCP Server (without Poetry)
# This script uses the Python virtual environment directly

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Python virtual environment path
VENV_PATH="/Users/kediasu/Library/Caches/pypoetry/virtualenvs/blender-docs-mcp-XT5HmYMo-py3.13"
PYTHON_BIN="$VENV_PATH/bin/python"

# Change to project directory
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found" >&2
    echo "Please copy .env.example to .env and configure your API keys" >&2
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH" >&2
    echo "Please run 'poetry install' first to create the virtual environment" >&2
    exit 1
fi

# Load environment variables from .env
set -a
source .env
set +a

# Start the server using the virtual environment's Python
exec "$PYTHON_BIN" src/server.py