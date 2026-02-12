# Search Engine - Embed query → pgvector top 30 → AI rerank → Return top 5

import time
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy import select, text

from src.database.models import Listing
from src.database import get_session
from src.embeddings import get_embedding_generator
from src.ai_parser import get_ai_parser


class SearchEngine:
    
    def __init__(self):
        self.embedding_gen = get_embedding_generator()
        self.ai_parser = get_ai_parser()
    
    async def search(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search pipeline:
        1. Embed query text
        2. pgvector cosine similarity → top 50 candidates
        3. AI rerank candidates by relevance
        4. Return top `limit` results
        """
        start_time = time.time()
        
        # Step 1: Embed query
        query_embedding = self.embedding_gen.generate_embedding(query_text)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []
        
        # Step 2: pgvector similarity search - get 50 candidates (more options for reranker)
        candidates = await self._find_similar(query_embedding, candidate_limit=50)
        
        if not candidates:
            logger.info(f"No candidates found for: '{query_text}'")
            return []
        
        # Step 3: AI rerank
        relevant_indices = self.ai_parser.rerank(query_text, candidates)
        
        # Step 4: Pick top results
        results = [candidates[i] for i in relevant_indices[:limit]]
        
        ms = int((time.time() - start_time) * 1000)
        logger.info(f"Search: '{query_text}' → {len(candidates)} candidates → {len(results)} results ({ms}ms)")
        
        return results
    
    async def _find_similar(
        self, query_embedding: List[float], candidate_limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Find similar listings using pgvector cosine similarity."""
        async with get_session() as session:
            query = select(
                Listing,
                (1 - Listing.embedding.cosine_distance(query_embedding)).label('similarity')
            ).order_by(
                text('similarity DESC')
            ).limit(candidate_limit)
            
            result = await session.execute(query)
            rows = result.all()
        
        candidates = []
        for listing, similarity in rows:
            candidates.append({
                'id': listing.id,
                'source_channel': listing.source_channel,
                'source_message_id': listing.source_message_id,
                'raw_text': listing.raw_text,
                'has_media': listing.has_media,
                'created_at': listing.created_at.isoformat() if listing.created_at else None,
                'similarity_score': float(similarity),
            })
        
        return candidates


# Singleton
_search_engine: Optional[SearchEngine] = None

def get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
