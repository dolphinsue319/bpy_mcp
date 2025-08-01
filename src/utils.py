"""Utility functions for the Blender MCP server."""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_env_var(key: str, default: str = None) -> str:
    """Get environment variable with optional default."""
    
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} not found and no default provided")
    return value


def format_search_result(matches: List[Any], query: str) -> str:
    """Format Pinecone search results for display."""
    
    if not matches:
        return f"No results found for '{query}'"
    
    output = [f"Search results for '{query}':\n"]
    
    for i, match in enumerate(matches, 1):
        # Handle both Pinecone match objects and cached dict format
        if hasattr(match, 'metadata'):
            # Pinecone match object
            metadata = match.metadata
            score = match.score
        else:
            # Cached dict format
            metadata = match.get('metadata', {})
            score = match.get('score', 0)
        
        # Extract info from metadata
        func_path = metadata.get('function_path', 'Unknown')
        description = metadata.get('description', 'No description')
        doc_type = metadata.get('doc_type', 'unknown')
        module = metadata.get('module', '')
        
        # Format the result
        output.append(f"{i}. **{func_path}** ({doc_type})")
        output.append(f"   Module: {module}")
        output.append(f"   Score: {score:.3f}")
        output.append(f"   {description[:150]}...")
        
        # Add signature if available
        if 'signature' in metadata and metadata['signature']:
            output.append(f"   Signature: `{metadata['signature']}`")
        
        output.append("")  # Empty line between results
    
    return '\n'.join(output)


def format_function_details(metadata: Dict[str, Any]) -> str:
    """Format detailed function information for display."""
    
    output = []
    
    # Header
    func_path = metadata.get('function_path', 'Unknown')
    doc_type = metadata.get('doc_type', 'unknown')
    output.append(f"# {func_path}")
    output.append(f"**Type**: {doc_type}")
    output.append("")
    
    # Description
    description = metadata.get('description', 'No description available')
    output.append("## Description")
    output.append(description)
    output.append("")
    
    # Signature
    if 'signature' in metadata and metadata['signature']:
        output.append("## Signature")
        output.append(f"```python")
        output.append(metadata['signature'])
        output.append("```")
        output.append("")
    
    # Parameters
    if 'parameters' in metadata and metadata['parameters']:
        output.append("## Parameters")
        for param in metadata['parameters']:
            name = param.get('name', 'unknown')
            param_type = param.get('type', 'unknown')
            desc = param.get('description', '')
            output.append(f"- **{name}** ({param_type}): {desc}")
        output.append("")
    
    # Example
    if 'example_code' in metadata and metadata['example_code']:
        output.append("## Example")
        output.append("```python")
        output.append(metadata['example_code'])
        output.append("```")
        output.append("")
    
    # Module info
    if 'module' in metadata:
        output.append(f"**Module**: {metadata['module']}")
    
    return '\n'.join(output)


def prepare_text_for_embedding(entry: Dict[str, Any]) -> str:
    """Prepare document text for embedding generation."""
    
    parts = []
    
    # Function path is most important
    func_path = entry.get('function_path', '')
    if func_path:
        parts.append(f"Function: {func_path}")
    
    # Module context
    module = entry.get('module', '')
    if module:
        parts.append(f"Module: {module}")
    
    # Type
    doc_type = entry.get('doc_type', '')
    if doc_type:
        parts.append(f"Type: {doc_type}")
    
    # Description
    description = entry.get('description', '')
    if description:
        parts.append(f"Description: {description}")
    
    # Signature
    signature = entry.get('signature', '')
    if signature:
        parts.append(f"Signature: {signature}")
    
    # Parameters (condensed)
    if 'parameters' in entry and entry['parameters']:
        param_names = [p.get('name', '') for p in entry['parameters'] if p.get('name')]
        if param_names:
            parts.append(f"Parameters: {', '.join(param_names)}")
    
    return '\n\n'.join(parts)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size."""
    
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]