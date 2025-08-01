#!/bin/bash
# Update Pinecone index with latest Blender documentation

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

echo -e "${BLUE}🔄 Blender Docs Index Update${NC}"
echo "======================================="
echo ""

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please run ./scripts/setup.sh first"
    exit 1
fi

source venv/bin/activate

# Check environment
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check documentation
if [ ! -d "blender_python_reference_4_5" ] || [ -z "$(ls -A blender_python_reference_4_5 2>/dev/null)" ]; then
    echo -e "${RED}❌ Blender documentation not found${NC}"
    echo "Please download and extract documentation to blender_python_reference_4_5/"
    exit 1
fi

# Backup current index summary if it exists
if [ -f "index_summary.json" ]; then
    backup_name="index_summary_$(date +%Y%m%d_%H%M%S).json"
    cp index_summary.json "backups/$backup_name" 2>/dev/null || mkdir -p backups && cp index_summary.json "backups/$backup_name"
    echo -e "${GREEN}✓ Backed up current index summary${NC}"
fi

# Count files
file_count=$(find blender_python_reference_4_5 -name "*.html" | wc -l)
echo -e "${GREEN}Found $file_count HTML files to process${NC}"
echo ""

# Confirmation
echo -e "${YELLOW}⚠️  This will rebuild the entire Pinecone index${NC}"
echo "This process will:"
echo "  - Parse all HTML documentation files"
echo "  - Generate embeddings using OpenAI API"
echo "  - Upload vectors to Pinecone"
echo ""
echo "Estimated time: 5-10 minutes"
echo "Estimated cost: ~\$0.10 USD"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo -e "${GREEN}Starting index update...${NC}"
echo ""

# Run the indexer
python src/indexer.py

echo ""
echo -e "${GREEN}✅ Index update complete!${NC}"

# Show summary
if [ -f "index_summary.json" ]; then
    echo ""
    echo "Index Summary:"
    echo "=============="
    total_entries=$(python -c "import json; print(json.load(open('index_summary.json'))['total_entries'])")
    echo "Total entries indexed: $total_entries"
    
    # Show some module statistics
    python -c "
import json
data = json.load(open('index_summary.json'))
modules = data.get('modules', [])
print(f'Modules indexed: {len(modules)}')
if len(modules) > 5:
    print('Top modules:', ', '.join(modules[:5]), '...')
else:
    print('Modules:', ', '.join(modules))
"
fi

echo ""
echo "The MCP server is now ready to use with the updated index!"