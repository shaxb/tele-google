"""Search pipeline: embed query → pgvector top 50 → AI rerank → top N results.
Deal detection: embed listing → pgvector neighbors → median price comparison.
"""

import statistics
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
                "metadata": listing.item_metadata,
                "price": listing.price,
                "currency": listing.currency,
            }
            for listing, sim in rows
        ]

    # ------------------------------------------------------------------
    # Deal detection: median-neighbor algorithm
    # ------------------------------------------------------------------

    async def evaluate_deal(
        self,
        embedding: List[float],
        price: float,
        currency: str,
        neighbor_limit: int = 10,
        min_similarity: float = 0.85,
        min_neighbors: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Compare a listing's price against its nearest neighbors' median.

        Returns a dict with deal analysis, or None if not enough comparable data.
        """
        candidates = await self._find_similar(embedding, candidate_limit=neighbor_limit)

        # Filter: same currency, has price, and high enough similarity
        neighbors = [
            c for c in candidates
            if c["price"] is not None
            and c["currency"] == currency
            and c["similarity_score"] >= min_similarity
        ]

        if len(neighbors) < min_neighbors:
            return None

        prices = [n["price"] for n in neighbors]
        median_price = statistics.median(prices)

        if median_price == 0:
            return None

        deviation = (price - median_price) / median_price

        return {
            "median_price": round(median_price, 2),
            "neighbor_count": len(neighbors),
            "neighbor_prices": sorted(prices),
            "deviation": round(deviation, 4),
            "is_deal": deviation <= -0.15,
            "is_overpriced": deviation >= 0.15,
            "verdict": (
                "deal" if deviation <= -0.15
                else "overpriced" if deviation >= 0.15
                else "market_price"
            ),
        }


_instance: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    global _instance
    if _instance is None:
        _instance = SearchEngine()
    return _instance
