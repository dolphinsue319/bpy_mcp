"""Build Pinecone index for Blender documentation."""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
import logging
from tqdm import tqdm

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

from parser import parse_all_docs, DocEntry
from utils import get_env_var, prepare_text_for_embedding, chunk_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlenderIndexer:
    """Handles indexing of Blender documentation to Pinecone."""
    
    def __init__(self):
        # Initialize clients
        self.openai_client = OpenAI(api_key=get_env_var('OPENAI_API_KEY'))
        self.pinecone_client = Pinecone(api_key=get_env_var('PINECONE_API_KEY'))
        
        self.index_name = get_env_var('PINECONE_INDEX_NAME', 'blender-docs')
        self.embedding_model = "text-embedding-3-small"
        self.dimension = 1536
        
    def create_index(self):
        """Create Pinecone index if it doesn't exist."""
        
        existing_indexes = self.pinecone_client.list_indexes()
        
        if self.index_name not in [idx.name for idx in existing_indexes]:
            logger.info(f"Creating index '{self.index_name}'...")
            
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            
            # Wait for index to be ready
            logger.info("Waiting for index to be ready...")
            import time
            time.sleep(10)
        else:
            logger.info(f"Index '{self.index_name}' already exists")
        
        return self.pinecone_client.Index(self.index_name)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        
        # OpenAI allows up to 2048 inputs in a single request
        # But we'll use smaller batches to avoid rate limits
        batch_size = 100
        all_embeddings = []
        
        for batch in chunk_list(texts, batch_size):
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
            
            # Small delay to avoid rate limits
            import time
            time.sleep(0.1)
        
        return all_embeddings
    
    def prepare_vectors(self, entries: List[DocEntry]) -> List[Dict[str, Any]]:
        """Prepare vector data for Pinecone upsert."""
        
        logger.info(f"Preparing {len(entries)} entries for indexing...")
        
        # Prepare texts for embedding
        texts = []
        for entry in entries:
            text = prepare_text_for_embedding(entry.__dict__)
            texts.append(text)
        
        # Generate embeddings in batches
        logger.info("Generating embeddings...")
        embeddings = self.batch_generate_embeddings(texts)
        
        # Prepare vector data
        vectors = []
        for i, (entry, embedding) in enumerate(zip(entries, embeddings)):
            # Create metadata
            metadata = {
                'function_path': entry.function_path,
                'title': entry.title,
                'description': entry.description[:1000],  # Limit description length
                'module': entry.module,
                'doc_type': entry.doc_type,
                'has_signature': bool(entry.signature),
                'has_parameters': bool(entry.parameters),
                'parameter_count': len(entry.parameters) if entry.parameters else 0
            }
            
            # Add signature if not too long
            if entry.signature and len(entry.signature) < 500:
                metadata['signature'] = entry.signature
            
            # Add parameter names
            if entry.parameters:
                param_names = [p.get('name', '') for p in entry.parameters[:10]]  # Limit to 10
                metadata['parameter_names'] = ', '.join(param_names)
            
            vectors.append({
                'id': entry.function_path,
                'values': embedding,
                'metadata': metadata
            })
        
        return vectors
    
    def index_documents(self, docs_dir: Path):
        """Index all documents from the documentation directory."""
        
        # Parse all documents
        logger.info(f"Parsing documents from {docs_dir}")
        entries = parse_all_docs(docs_dir)
        
        if not entries:
            logger.error("No entries found to index!")
            return
        
        # Create/get index
        index = self.create_index()
        
        # Prepare vectors
        vectors = self.prepare_vectors(entries)
        
        # Upsert to Pinecone in batches
        logger.info(f"Uploading {len(vectors)} vectors to Pinecone...")
        batch_size = 100
        
        for i in tqdm(range(0, len(vectors), batch_size)):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
        
        logger.info("Indexing complete!")
        
        # Print some statistics
        stats = index.describe_index_stats()
        logger.info(f"Index stats: {stats}")
        
        # Save a summary for reference
        summary = {
            'total_entries': len(entries),
            'index_name': self.index_name,
            'embedding_model': self.embedding_model,
            'modules': list(set(e.module for e in entries if e.module)),
            'doc_types': list(set(e.doc_type for e in entries))
        }
        
        summary_path = Path(__file__).parent.parent / 'index_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary saved to {summary_path}")


def main():
    """Main function to run the indexer."""
    
    # Check environment variables
    required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY']
    for var in required_vars:
        try:
            get_env_var(var)
        except ValueError:
            logger.error(f"Missing required environment variable: {var}")
            logger.error("Please create a .env file with the required API keys")
            return
    
    # Get documentation directory
    docs_dir = Path(__file__).parent.parent / "blender_python_reference_4_5"
    
    if not docs_dir.exists():
        logger.error(f"Documentation directory not found: {docs_dir}")
        return
    
    # Run indexer
    indexer = BlenderIndexer()
    indexer.index_documents(docs_dir)


if __name__ == "__main__":
    main()