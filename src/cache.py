"""
Local SQLite cache for Blender documentation queries.
Reduces API calls and improves response time.
"""

import sqlite3
import json
import time
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


class DocumentationCache:
    """SQLite-based cache for documentation search results."""
    
    def __init__(self, cache_dir: str = ".cache", ttl_seconds: int = 86400):
        """
        Initialize cache with configurable TTL.
        
        Args:
            cache_dir: Directory to store cache database
            ttl_seconds: Time to live in seconds (default: 24 hours)
        """
        # Support environment variable override
        cache_dir = os.getenv('BLENDER_CACHE_DIR', cache_dir)
        ttl_seconds = int(os.getenv('CACHE_TTL_SECONDS', str(ttl_seconds)))
        
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(exist_ok=True)
        except PermissionError as e:
            logger.error(f"Cannot create cache directory {self.cache_dir}: {e}")
            logger.warning("Cache will be disabled for this session")
            # Set a flag to disable cache operations
            self.disabled = True
            return
        
        self.disabled = False
        self.db_path = self.cache_dir / "blender_docs_cache.db"
        self.ttl_seconds = ttl_seconds
        
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    results TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS function_cache (
                    function_path TEXT PRIMARY KEY,
                    details TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indices for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_created 
                ON search_cache(created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_function_created 
                ON function_cache(created_at)
            """)
            
            conn.commit()
    
    def _hash_query(self, query: str, limit: int) -> str:
        """Generate consistent hash for query + limit combination."""
        key = f"{query.lower().strip()}:{limit}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_search_results(self, query: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached search results if available and not expired.
        
        Returns:
            List of search results or None if not cached/expired
        """
        if self.disabled:
            return None
            
        query_hash = self._hash_query(query, limit)
        current_time = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT results, created_at 
                FROM search_cache 
                WHERE query_hash = ?
            """, (query_hash,))
            
            row = cursor.fetchone()
            if row:
                results_json, created_at = row
                
                # Check if cache is still valid
                if current_time - created_at < self.ttl_seconds:
                    # Update hit count
                    conn.execute("""
                        UPDATE search_cache 
                        SET hit_count = hit_count + 1 
                        WHERE query_hash = ?
                    """, (query_hash,))
                    conn.commit()
                    
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return json.loads(results_json)
                else:
                    # Cache expired, remove it
                    conn.execute("DELETE FROM search_cache WHERE query_hash = ?", (query_hash,))
                    conn.commit()
                    logger.info(f"Cache expired for query: {query[:50]}...")
        
        return None
    
    def cache_search_results(self, query: str, limit: int, results: List[Dict[str, Any]]):
        """Cache search results."""
        if self.disabled:
            return
            
        query_hash = self._hash_query(query, limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO search_cache 
                (query_hash, query, results, created_at) 
                VALUES (?, ?, ?, ?)
            """, (
                query_hash,
                query,
                json.dumps(results),
                time.time()
            ))
            conn.commit()
            logger.info(f"Cached results for query: {query[:50]}...")
    
    def get_function_details(self, function_path: str) -> Optional[Dict[str, Any]]:
        """Get cached function details if available."""
        if self.disabled:
            return None
            
        current_time = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT details, created_at 
                FROM function_cache 
                WHERE function_path = ?
            """, (function_path,))
            
            row = cursor.fetchone()
            if row:
                details_json, created_at = row
                
                if current_time - created_at < self.ttl_seconds:
                    conn.execute("""
                        UPDATE function_cache 
                        SET hit_count = hit_count + 1 
                        WHERE function_path = ?
                    """, (function_path,))
                    conn.commit()
                    
                    logger.info(f"Cache hit for function: {function_path}")
                    return json.loads(details_json)
                else:
                    conn.execute("DELETE FROM function_cache WHERE function_path = ?", (function_path,))
                    conn.commit()
        
        return None
    
    def cache_function_details(self, function_path: str, details: Dict[str, Any]):
        """Cache function details."""
        if self.disabled:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO function_cache 
                (function_path, details, created_at) 
                VALUES (?, ?, ?)
            """, (
                function_path,
                json.dumps(details),
                time.time()
            ))
            conn.commit()
            logger.info(f"Cached details for function: {function_path}")
    
    def clear_expired(self):
        """Remove all expired cache entries."""
        if self.disabled:
            return 0
            
        current_time = time.time()
        expired_time = current_time - self.ttl_seconds
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM search_cache WHERE created_at < ?
            """, (expired_time,))
            search_deleted = cursor.rowcount
            
            cursor = conn.execute("""
                DELETE FROM function_cache WHERE created_at < ?
            """, (expired_time,))
            function_deleted = cursor.rowcount
            
            conn.commit()
            
        logger.info(f"Cleared {search_deleted} expired search results and {function_deleted} expired function details")
        return search_deleted + function_deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.disabled:
            return {
                "search_entries": 0,
                "function_entries": 0,
                "total_entries": 0,
                "search_hits": 0,
                "function_hits": 0,
                "total_hits": 0,
                "database_size_mb": 0,
                "ttl_hours": self.ttl_seconds / 3600,
                "status": "disabled"
            }
            
        with sqlite3.connect(self.db_path) as conn:
            # Count entries
            search_count = conn.execute("SELECT COUNT(*) FROM search_cache").fetchone()[0]
            function_count = conn.execute("SELECT COUNT(*) FROM function_cache").fetchone()[0]
            
            # Get hit counts
            search_hits = conn.execute("SELECT SUM(hit_count) FROM search_cache").fetchone()[0] or 0
            function_hits = conn.execute("SELECT SUM(hit_count) FROM function_cache").fetchone()[0] or 0
            
            # Get database size
            db_size = self.db_path.stat().st_size
            
        return {
            "search_entries": search_count,
            "function_entries": function_count,
            "total_entries": search_count + function_count,
            "search_hits": search_hits,
            "function_hits": function_hits,
            "total_hits": search_hits + function_hits,
            "database_size_mb": round(db_size / 1024 / 1024, 2),
            "ttl_hours": self.ttl_seconds / 3600
        }
    
    def clear_all(self):
        """Clear all cache entries."""
        if self.disabled:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM search_cache")
            conn.execute("DELETE FROM function_cache")
            conn.commit()
        logger.info("Cleared all cache entries")