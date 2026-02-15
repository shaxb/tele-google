"""AI pipeline — listing classification and search result reranking via OpenAI."""

import json
import time
from typing import Any, Dict, List, Optional
from loguru import logger
from openai import AsyncOpenAI, OpenAIError

from src.config import get_config
from src.prompts import LISTING_CHECK_PROMPT, RERANK_PROMPT, create_listing_check_prompt, create_rerank_prompt


class AIParser:
    def __init__(self) -> None:
        cfg = get_config()
        self.client = AsyncOpenAI(api_key=cfg.openai.api_key)
        self.model = cfg.openai.model

    async def _call(self, system: str, user: str, temperature: float = 0.2) -> Optional[Dict[str, Any]]:
        """Send an async chat completion request expecting JSON back."""
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            return json.loads(content) if content else None
        except (OpenAIError, json.JSONDecodeError) as e:
            logger.error(f"OpenAI error: {e}")
            return None

    async def classify_and_extract(self, text: str) -> Optional[Dict[str, Any]]:
        """Classify text and extract metadata if it's a listing.

        Returns a dict with keys:
          - "metadata": the extracted fields (price, currency, category, etc.)
          - "confidence": float 0–1
          - "raw_response": the raw JSON string from OpenAI
          - "processing_time_ms": int
        Or None if the message is not a listing.
        """
        start = time.monotonic()
        result = await self._call(LISTING_CHECK_PROMPT, create_listing_check_prompt(text), temperature=0.1)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if not result or not result.get("is_listing"):
            return None

        metadata = result.get("metadata") or {}
        confidence = result.get("confidence", 0.0)

        return {
            "metadata": metadata,
            "confidence": float(confidence),
            "raw_response": json.dumps(result, ensure_ascii=False),
            "processing_time_ms": elapsed_ms,
        }

    async def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[int]:
        """Return ordered indices of the most relevant candidates for *query*."""
        if not candidates:
            return []
        result = await self._call(RERANK_PROMPT, create_rerank_prompt(query, candidates))
        if not result:
            return list(range(min(5, len(candidates))))
        indices = result.get("relevant_indices", [])
        return [i for i in indices if isinstance(i, int) and 0 <= i < len(candidates)]


_instance: Optional[AIParser] = None


def get_ai_parser() -> AIParser:
    global _instance
    if _instance is None:
        _instance = AIParser()
    return _instance
