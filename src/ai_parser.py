"""AI pipeline — listing classification and search result reranking via OpenAI."""

import json
from typing import Any, Dict, List, Optional
from loguru import logger
from openai import OpenAI, OpenAIError

from src.config import get_config
from src.prompts import LISTING_CHECK_PROMPT, RERANK_PROMPT, create_listing_check_prompt, create_rerank_prompt


class AIParser:
    def __init__(self) -> None:
        cfg = get_config()
        self.client = OpenAI(api_key=cfg.openai.api_key)
        self.model = cfg.openai.model

    def _call(self, system: str, user: str, temperature: float = 0.2) -> Optional[Dict[str, Any]]:
        """Send a chat completion request expecting JSON back."""
        try:
            resp = self.client.chat.completions.create(
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

    def is_listing(self, text: str) -> bool:
        """Return True if *text* looks like a marketplace listing."""
        result = self._call(LISTING_CHECK_PROMPT, create_listing_check_prompt(text), temperature=0.1)
        return bool(result and result.get("is_listing"))

    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[int]:
        """Return ordered indices of the most relevant candidates for *query*."""
        if not candidates:
            return []
        result = self._call(RERANK_PROMPT, create_rerank_prompt(query, candidates))
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
