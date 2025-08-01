# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Blender Python SDK Documentation MCP (Model Context Protocol) server that provides semantic search capabilities for Blender's Python API documentation. The server indexes 2,050+ HTML documentation files and serves them through MCP tools for use with Claude Code and Raycast.

## Configuration Paths

- `/Users/kediasu/Library/Application Support/Claude/claude_desktop_config.json` is the configuration file for setting the MCP path in Claude app

## Key Commands

### Development Setup
```bash
# Initial setup (installs Poetry if needed)
./scripts/setup.sh

# Install/update dependencies
poetry install

# Run the MCP server
./scripts/start-server.sh
# or manually:
poetry run python src/server.py

# Update Pinecone index (required after documentation changes)
./scripts/update-index.sh
# or manually:
poetry run python src/indexer.py
```

### Testing & Linting
```bash
# Run tests
poetry run pytest

# Format code
poetry run black src/
poetry run isort src/

# Type checking
poetry run mypy src/

# Linting
poetry run flake8 src/
```

## Architecture Overview

### Core Components

1. **MCP Server (`src/server.py`)**
   - FastMCP-based server exposing 4 tools: `search_docs`, `get_function`, `list_modules`, `cache_stats`
   - Uses global clients for OpenAI and Pinecone connections
   - Integrates SQLite cache for performance optimization

2. **Document Indexing Pipeline**
   - `src/parser.py`: Parses Blender HTML docs into structured `DocEntry` objects
   - `src/indexer.py`: Generates OpenAI embeddings and uploads to Pinecone vector database
   - Processes files in batches of 100 for rate limiting compliance

3. **Caching Layer (`src/cache.py`)**
   - SQLite-based local cache with 24-hour TTL
   - Caches both search results and function details
   - Graceful fallback when cache directory permissions fail
   - Environment variable support: `BLENDER_CACHE_DIR`, `CACHE_TTL_SECONDS`

### Data Flow

1. **Indexing**: HTML files → Parser → DocEntry objects → OpenAI embeddings → Pinecone vectors
2. **Search**: Query → Cache check → OpenAI embedding → Pinecone similarity search → Formatted results
3. **Function lookup**: Function path → Cache check → Pinecone fetch/search → Detailed info

### External Dependencies

- **OpenAI API**: For generating text-embedding-3-small vectors (1536 dimensions)
- **Pinecone**: Vector database for semantic search (requires manual index creation)
- **Blender Documentation**: HTML files in `blender_python_reference_4_5/` (not in version control)

## Environment Configuration

Required environment variables in `.env`:
- `OPENAI_API_KEY`: For embeddings generation
- `PINECONE_API_KEY`: For vector database access
- `PINECONE_INDEX_NAME`: Index name (default: "blender-docs")

Optional:
- `BLENDER_CACHE_DIR`: Cache directory location (default: ".cache")
- `CACHE_TTL_SECONDS`: Cache expiration time (default: 86400)

## MCP Integration

The server is designed to be used as an MCP server in Claude Code:
```json
{
  "mcpServers": {
    "blender-docs": {
      "command": "/absolute/path/to/bpy_mcp/scripts/start-server.sh"
    }
  }
}
```

## Important Considerations

1. **Python Version**: Requires Python 3.10+ (updated from 3.8)
2. **Poetry**: All dependency management uses Poetry, not pip or virtualenv
3. **Shell Scripts**: All scripts in `scripts/` have execute permissions and handle environment setup
4. **Cache**: The `.cache/` directory and `index_summary.json` are git-ignored
5. **Documentation Source**: The `blender_python_reference_4_5/` directory must be populated manually with Blender HTML docs

## Common Development Tasks

### Adding New MCP Tools
1. Add new async function decorated with `@mcp.tool()` in `src/server.py`
2. Follow existing patterns for error handling and cache integration
3. Update README.md with tool documentation

### Modifying Parser Logic
1. Edit `src/parser.py` to handle new HTML structures
2. Update `DocEntry` dataclass if new fields are needed
3. Re-run indexer to update Pinecone database

### Debugging Cache Issues
- Check cache stats with the `cache_stats()` MCP tool
- Cache database is at `.cache/blender_docs_cache.db`
- Clear cache by deleting `.cache/` directory

### Performance Optimization
- Batch size for embeddings is set to 100 in `src/indexer.py`
- Cache TTL can be adjusted via `CACHE_TTL_SECONDS` environment variable
- Consider adding indexes to SQLite cache for large-scale usage