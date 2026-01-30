"""
Meilisearch Wrapper
Handles search index initialization, document indexing, and search queries
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import meilisearch
from meilisearch.index import Index
from meilisearch.errors import MeilisearchApiError
from meilisearch.task import TaskInfo  # type: ignore
from meilisearch.models.index import IndexStats  # type: ignore

from src.config import get_config
from src.utils.logger import get_logger

log = get_logger(__name__)


class SearchEngine:
    """
    Meilisearch client wrapper for the marketplace index
    
    Implements the exact index configuration from PROJECT_GUIDE.md Section 7
    """
    
    def __init__(self):
        """Initialize Meilisearch client"""
        config = get_config()
        meili = config.meilisearch
        
        self.client = meilisearch.Client(meili.host, meili.master_key)
        self.index_name = meili.index
        self._index: Optional[Index] = None
        
        log.info(f"Meilisearch client initialized: {meili.host}")
    
    async def initialize_index(self) -> None:
        """
        Create and configure the marketplace index
        
        Sets up:
        - Filterable attributes: category, subcategory, price, data.*, channel
        - Searchable attributes: item, searchable_text, data, category
        - Sortable attributes: price, posted_at
        - Typo tolerance: enabled (max 2 typos)
        """
        try:
            # Create index if doesn't exist
            try:
                self._index = self.client.get_index(self.index_name)
                log.info(f"Index '{self.index_name}' already exists")
            except MeilisearchApiError as e:
                if "index_not_found" in str(e):
                    self.client.create_index(self.index_name, {"primaryKey": "id"})
                    self._index = self.client.get_index(self.index_name)
                    log.info(f"Created new index: '{self.index_name}'")
                else:
                    raise
            
            # Configure filterable attributes
            # data.* allows filtering on any nested field (data.brand, data.color, etc.)
            self._index.update_filterable_attributes([
                "category",
                "subcategory", 
                "price",
                "data",  # Enables filtering on all nested data fields
                "channel",
                "posted_at"
            ])
            log.info("Configured filterable attributes")
            
            # Configure searchable attributes (ranked by importance)
            self._index.update_searchable_attributes([
                "item",            # Most important: human-readable item name
                "searchable_text", # Combined searchable content
                "data",            # All category-specific fields
                "category"         # Category names
            ])
            log.info("Configured searchable attributes")
            
            # Configure sortable attributes
            self._index.update_sortable_attributes([
                "price",
                "posted_at"
            ])
            log.info("Configured sortable attributes")
            
            # Configure typo tolerance (PROJECT_GUIDE.md: maxTypos: 2)
            # This enables "ayfon" → "iPhone" search
            self._index.update_typo_tolerance({
                "enabled": True,
                "minWordSizeForTypos": {
                    "oneTypo": 4,   # 4+ char words: 1 typo allowed
                    "twoTypos": 8   # 8+ char words: 2 typos allowed
                }
            })
            log.info("Configured typo tolerance")
            
            # Configure ranking rules (default order optimized for marketplace)
            self._index.update_ranking_rules([
                "words",      # Number of matching words
                "typo",       # Fewer typos = higher rank
                "proximity",  # Word proximity in text
                "attribute",  # Searchable attribute order
                "sort",       # Custom sort (price, date)
                "exactness"   # Exact matches first
            ])
            log.info("Configured ranking rules")
            
            log.info(f"Index '{self.index_name}' fully configured")
            
        except Exception as e:
            log.error(f"Failed to initialize index: {e}")
            raise
    
    def get_index(self) -> Index:
        """Get the marketplace index"""
        if self._index is None:
            self._index = self.client.get_index(self.index_name)
        return self._index
    
    async def add_document(self, document: Dict[str, Any]) -> TaskInfo:
        """
        Add a single document to the index
        
        Args:
            document: Document following the structure from PROJECT_GUIDE.md Section 7
                {
                    "id": "channel_messageid",
                    "category": "electronics",
                    "subcategory": "smartphone",
                    "item": "iPhone 15 Pro",
                    "data": {...},  # Category-specific fields
                    "price": 750,
                    "currency": "USD",
                    "searchable_text": "...",
                    "images": [...],
                    "message_link": "...",
                    "channel": "@MalikaBozor",
                    "posted_at": "2026-01-30T10:30:00Z"
                }
        
        Returns:
            Task info from Meilisearch
        """
        try:
            index = self.get_index()
            result = index.add_documents([document])
            log.info(f"Added document: {document['id']}")
            return result
        except Exception as e:
            log.error(f"Failed to add document {document.get('id')}: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> TaskInfo:
        """
        Add multiple documents to the index (batch operation)
        
        Args:
            documents: List of documents
        
        Returns:
            Task info from Meilisearch
        """
        try:
            index = self.get_index()
            result = index.add_documents(documents)
            log.info(f"Added {len(documents)} documents")
            return result
        except Exception as e:
            log.error(f"Failed to add documents: {e}")
            raise
    
    async def update_document(self, document: Dict[str, Any]) -> TaskInfo:
        """Update a single document"""
        try:
            index = self.get_index()
            result = index.update_documents([document])
            log.info(f"Updated document: {document['id']}")
            return result
        except Exception as e:
            log.error(f"Failed to update document {document.get('id')}: {e}")
            raise
    
    async def delete_document(self, document_id: str) -> TaskInfo:
        """Delete a document by ID"""
        try:
            index = self.get_index()
            result = index.delete_document(document_id)
            log.info(f"Deleted document: {document_id}")
            return result
        except Exception as e:
            log.error(f"Failed to delete document {document_id}: {e}")
            raise
    
    async def search(
        self,
        query: str,
        filters: Optional[str] = None,
        sort: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
        facets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search the marketplace index
        
        Args:
            query: Search text (e.g., "iPhone 15")
            filters: Meilisearch filter string (e.g., "category = electronics AND price <= 800")
            sort: List of sort rules (e.g., ["price:asc", "posted_at:desc"])
            limit: Number of results to return (pagination)
            offset: Offset for pagination
            facets: Facets to return (e.g., ["category", "subcategory"] for counts)
        
        Returns:
            Search results with hits, facets, and metadata
            
        Example:
            results = await search_engine.search(
                query="iPhone 15",
                filters="category = electronics AND data.color = black AND price <= 800",
                sort=["price:asc"],
                limit=10
            )
        """
        try:
            index = self.get_index()
            
            # Build search params
            search_params: Dict[str, Any] = {
                "limit": limit,
                "offset": offset
            }
            
            if filters:
                search_params["filter"] = filters
            
            if sort:
                search_params["sort"] = sort
            
            if facets:
                search_params["facets"] = facets
            
            # Execute search
            results = index.search(query, search_params)
            
            log.info(
                f"Search: '{query}' | Filters: {filters} | "
                f"Results: {results['estimatedTotalHits']}"
            )
            
            return results
            
        except Exception as e:
            log.error(f"Search failed for query '{query}': {e}")
            raise
    
    async def get_stats(self) -> IndexStats:
        """Get index statistics"""
        try:
            index = self.get_index()
            stats = index.get_stats()
            return stats
        except Exception as e:
            log.error(f"Failed to get stats: {e}")
            raise
    
    async def clear_index(self) -> TaskInfo:
        """Delete all documents from the index (use with caution!)"""
        try:
            index = self.get_index()
            result = index.delete_all_documents()
            log.warning("Cleared all documents from index")
            return result
        except Exception as e:
            log.error(f"Failed to clear index: {e}")
            raise


# Global search engine instance
_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """
    Get global SearchEngine instance (singleton)
    
    Returns:
        SearchEngine instance
    """
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
