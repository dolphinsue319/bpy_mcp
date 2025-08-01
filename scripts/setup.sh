#!/bin/bash
# Setup script for Blender Docs MCP Server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔧 Blender Docs MCP Server Setup${NC}"
echo "======================================="
echo ""

cd "$PROJECT_ROOT"

# Check Python version
echo -e "${GREEN}1. Checking Python version...${NC}"
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo -e "   ✓ Python $python_version (OK)"
else
    echo -e "${RED}   ❌ Python $python_version is too old. Please install Python 3.8 or newer.${NC}"
    exit 1
fi

# Create virtual environment
echo -e "\n${GREEN}2. Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
else
    echo "   ✓ Virtual environment already exists"
fi

# Activate and install dependencies
source venv/bin/activate
echo -e "\n${GREEN}3. Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -e . > /dev/null 2>&1
echo "   ✓ Dependencies installed"

# Setup environment file
echo -e "\n${GREEN}4. Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "   ✓ Created .env file from template"
    echo -e "\n${YELLOW}   ⚠️  Please edit .env and add your API keys:${NC}"
    echo "      - OPENAI_API_KEY"
    echo "      - PINECONE_API_KEY"
    echo ""
    echo "   You can get these from:"
    echo "   - OpenAI: https://platform.openai.com/api-keys"
    echo "   - Pinecone: https://app.pinecone.io/"
else
    echo "   ✓ .env file already exists"
fi

# Check for Blender documentation
echo -e "\n${GREEN}5. Checking Blender documentation...${NC}"
if [ ! -d "blender_python_reference_4_5" ] || [ -z "$(ls -A blender_python_reference_4_5 2>/dev/null)" ]; then
    echo -e "   ${YELLOW}⚠️  Blender documentation not found${NC}"
    echo ""
    echo "   Please download Blender Python API documentation:"
    echo "   1. Visit: https://docs.blender.org/api/current/"
    echo "   2. Download the HTML documentation"
    echo "   3. Extract to: $PROJECT_ROOT/blender_python_reference_4_5/"
    echo ""
    docs_required=true
else
    file_count=$(find blender_python_reference_4_5 -name "*.html" | wc -l)
    echo "   ✓ Found $file_count HTML files"
    docs_required=false
fi

# Claude Code configuration
echo -e "\n${GREEN}6. Claude Code configuration:${NC}"
echo "   Add this to your Claude Code settings:"
echo ""
echo -e "${BLUE}   \"mcpServers\": {"
echo "     \"blender-docs\": {"
echo "       \"command\": \"$PROJECT_ROOT/scripts/start-server.sh\""
echo "     }"
echo -e "   }${NC}"

# Summary
echo -e "\n${GREEN}✅ Setup Summary:${NC}"
echo "======================================="

# Check if ready to go
all_ready=true

# Check API keys
if grep -q "^OPENAI_API_KEY=sk-" .env && grep -q "^PINECONE_API_KEY=..*-.*" .env; then
    echo "✓ API keys configured"
else
    echo -e "${YELLOW}⚠️  API keys need to be configured in .env${NC}"
    all_ready=false
fi

# Check docs
if [ "$docs_required" = true ]; then
    echo -e "${YELLOW}⚠️  Blender documentation needs to be downloaded${NC}"
    all_ready=false
else
    echo "✓ Blender documentation found"
fi

echo ""

if [ "$all_ready" = true ]; then
    echo -e "${GREEN}🎉 Setup complete! Next steps:${NC}"
    echo "1. Run the indexer to build the search index:"
    echo "   python src/indexer.py"
    echo ""
    echo "2. Start the MCP server:"
    echo "   ./scripts/start-server.sh"
else
    echo -e "${YELLOW}⚠️  Please complete the steps above before proceeding.${NC}"
fi

echo ""
echo "For more information, see README.md"