"""Search pipeline: embed query → pgvector top 50 → AI rerank → top N results.
Deal detection: embed listing → pgvector neighbors → median price comparison.
Valuation: embed query → find priced neighbors → return price statistics.
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
        query_embedding = await self.embedding_gen.generate(query_text)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        candidates = await self._find_similar(query_embedding, candidate_limit=50)
        if not candidates:
            return []

        indices = await self.ai_parser.rerank(query_text, candidates)
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

    # ------------------------------------------------------------------
    # Valuation: price check / "what is it worth?"
    # ------------------------------------------------------------------

    async def valuate(
        self,
        query_text: str,
        currency_filter: Optional[str] = None,
        neighbor_limit: int = 30,
        min_similarity: float = 0.80,
        min_samples: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Find similar listings with prices and return price statistics.

        Returns dict with median, mean, min, max, sample_count, sample_listings
        or None if insufficient data.
        """
        query_embedding = await self.embedding_gen.generate(query_text)
        if not query_embedding:
            return None

        candidates = await self._find_similar(query_embedding, candidate_limit=neighbor_limit)

        # Filter to priced listings with sufficient similarity
        priced = []
        for c in candidates:
            if (
                c["price"] is not None
                and c["price"] > 0
                and c["similarity_score"] >= min_similarity
            ):
                if currency_filter and c.get("currency") != currency_filter:
                    continue
                priced.append(c)

        if len(priced) < min_samples:
            return None

        prices = [c["price"] for c in priced]
        median = statistics.median(prices)
        mean = statistics.mean(prices)

        # Determine dominant currency
        currencies = [c.get("currency") for c in priced if c.get("currency")]
        dominant_currency = max(set(currencies), key=currencies.count) if currencies else "?"

        # Pick representative samples (closest to median)
        samples_sorted = sorted(priced, key=lambda c: abs(c["price"] - median))
        sample_listings = [
            {
                "title": (c.get("metadata") or {}).get("title", "?"),
                "price": c["price"],
                "currency": c.get("currency", "?"),
                "channel": c.get("source_channel", "?"),
                "message_id": c.get("source_message_id"),
                "similarity": round(c["similarity_score"], 3),
            }
            for c in samples_sorted[:5]
        ]

        return {
            "median_price": round(median, 2),
            "mean_price": round(mean, 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "sample_count": len(priced),
            "currency": dominant_currency,
            "sample_listings": sample_listings,
            "price_range_pct": round((max(prices) - min(prices)) / median * 100, 1) if median > 0 else 0,
        }


_instance: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    global _instance
    if _instance is None:
        _instance = SearchEngine()
    return _instance
