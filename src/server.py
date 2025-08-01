#!/usr/bin/env python3
"""MCP Server for Blender Python SDK documentation search."""

import logging
from typing import Optional

from fastmcp import FastMCP

from pinecone import Pinecone
from openai import AsyncOpenAI

from utils import get_env_var, format_search_result, format_function_details

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Blender Docs Search")

# Global clients (initialized in main)
openai_client: Optional[AsyncOpenAI] = None
pinecone_index = None
embedding_model = "text-embedding-3-small"


@mcp.tool()
async def search_docs(query: str, limit: int = 5) -> str:
    """
    Search Blender Python documentation using semantic search.
    
    Args:
        query: Natural language search query (e.g., "create mesh modifier")
        limit: Maximum number of results to return (1-20, default 5)
    
    Returns:
        Formatted search results with function paths and descriptions
    """
    
    # Validate limit
    limit = max(1, min(20, limit))
    
    try:
        # Generate embedding for query
        embedding_response = await openai_client.embeddings.create(
            model=embedding_model,
            input=query
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Search in Pinecone
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True
        )
        
        # Format results
        return format_search_result(results.matches, query)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error searching documentation: {str(e)}"


@mcp.tool()
async def get_function(function_path: str) -> str:
    """
    Get detailed information about a specific Blender API function or class.
    
    Args:
        function_path: Full path to function/class (e.g., "bpy.ops.mesh.subdivide")
    
    Returns:
        Detailed information including signature, parameters, and examples
    """
    
    try:
        # Fetch by ID from Pinecone
        fetch_response = pinecone_index.fetch(ids=[function_path])
        
        if function_path not in fetch_response.vectors:
            # Try a search instead
            embedding_response = await openai_client.embeddings.create(
                model=embedding_model,
                input=function_path
            )
            query_embedding = embedding_response.data[0].embedding
            
            results = pinecone_index.query(
                vector=query_embedding,
                top_k=1,
                include_metadata=True,
                filter={"function_path": {"$eq": function_path}}
            )
            
            if not results.matches:
                return f"Function '{function_path}' not found in documentation."
            
            metadata = results.matches[0].metadata
        else:
            metadata = fetch_response.vectors[function_path].metadata
        
        return format_function_details(metadata)
        
    except Exception as e:
        logger.error(f"Get function error: {e}")
        return f"Error retrieving function details: {str(e)}"


@mcp.tool()
async def list_modules(parent_module: Optional[str] = None) -> str:
    """
    List available Blender Python modules.
    
    Args:
        parent_module: Parent module to list submodules for (e.g., "bpy.ops")
    
    Returns:
        List of available modules
    """
    
    try:
        # For simplicity, we'll use a predefined list
        # In a real implementation, this could be dynamically generated
        modules = {
            None: ["bpy.ops", "bpy.types", "bpy.data", "bpy.context", "bmesh", "bgl", "blf", "aud"],
            "bpy.ops": ["mesh", "object", "scene", "material", "texture", "image", "curve", "armature"],
            "bpy.types": ["Mesh", "Object", "Scene", "Material", "Texture", "Image", "Curve", "Armature"],
            "bmesh": ["ops", "types", "utils", "geometry"],
        }
        
        available = modules.get(parent_module, [])
        
        if not available:
            return f"No submodules found for '{parent_module}'"
        
        output = [f"Modules under '{parent_module or 'root'}':\n" if parent_module else "Top-level modules:\n"]
        
        for module in available:
            full_path = f"{parent_module}.{module}" if parent_module else module
            output.append(f"- {full_path}")
        
        return '\n'.join(output)
        
    except Exception as e:
        logger.error(f"List modules error: {e}")
        return f"Error listing modules: {str(e)}"


if __name__ == "__main__":
    # Check environment variables
    required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY']
    for var in required_vars:
        try:
            get_env_var(var)
        except ValueError:
            logger.error(f"Missing required environment variable: {var}")
            logger.error("Please create a .env file with the required API keys")
            import sys
            sys.exit(1)
    
    # Initialize clients
    openai_client = AsyncOpenAI(api_key=get_env_var('OPENAI_API_KEY'))
    pinecone_client = Pinecone(api_key=get_env_var('PINECONE_API_KEY'))
    index_name = get_env_var('PINECONE_INDEX_NAME', 'blender-docs')
    pinecone_index = pinecone_client.Index(index_name)
    
    # Run server
    mcp.run()