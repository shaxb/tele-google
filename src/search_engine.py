"""Search pipeline: embed query → pgvector top 50 → AI rerank → top N results."""

from typing import Any, Dict, List, Optional
from loguru import logger
from sqlalchemy import select, text

from src.database.models import Listing
from src.database import get_session
from src.embeddings import get_embedding_generator
from src.ai_parser import get_ai_parser


class SearchEngine:
    def __init__(self) -> None:
        self.embedding_gen = get_embedding_generator()
        self.ai_parser = get_ai_parser()

    async def search(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_gen.generate(query_text)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        candidates = await self._find_similar(query_embedding, candidate_limit=50)
        if not candidates:
            return []

        indices = self.ai_parser.rerank(query_text, candidates)
        return [candidates[i] for i in indices[:limit]]

    async def _find_similar(self, embedding: List[float], candidate_limit: int = 50) -> List[Dict[str, Any]]:
        async with get_session() as session:
            rows = (await session.execute(
                select(
                    Listing,
                    (1 - Listing.embedding.cosine_distance(embedding)).label("similarity"),
                )
                .order_by(text("similarity DESC"))
                .limit(candidate_limit)
            )).all()

        return [
            {
                "id": listing.id,
                "source_channel": listing.source_channel,
                "source_message_id": listing.source_message_id,
                "raw_text": listing.raw_text,
                "has_media": listing.has_media,
                "created_at": listing.created_at.isoformat() if listing.created_at else None,
                "similarity_score": float(sim),
            }
            for listing, sim in rows
        ]


_instance: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    global _instance
    if _instance is None:
        _instance = SearchEngine()
    return _instance
