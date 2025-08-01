#!/bin/bash
# Start script for Blender Docs MCP Server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}🚀 Starting Blender Docs MCP Server${NC}"
echo "Project root: $PROJECT_ROOT"

# Change to project directory
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your API keys:"
    echo "  cp .env.example .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -e .
else
    source venv/bin/activate
fi

# Verify required environment variables
echo -e "${GREEN}✓ Checking environment variables...${NC}"
required_vars=("OPENAI_API_KEY" "PINECONE_API_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || [ -z "$(grep "^${var}=" .env | cut -d'=' -f2)" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Error: Missing required environment variables:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    echo "Please edit .env and add the missing API keys"
    exit 1
fi

# Check if Pinecone index exists
echo -e "${GREEN}✓ Environment configured${NC}"
echo ""
echo "Starting MCP server..."
echo "Your Claude Code should be configured to use:"
echo "  Command: $PROJECT_ROOT/scripts/start-server.sh"
echo ""

# Start the server
exec python src/server.py