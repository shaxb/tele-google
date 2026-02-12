"""OpenAI embedding generation for semantic search (text-embedding-3-small, 1536-dim)."""

from typing import List, Optional
from loguru import logger
from openai import OpenAI, OpenAIError

from src.config import get_config

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536


class EmbeddingGenerator:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=get_config().openai.api_key)

    def generate(self, text: str) -> Optional[List[float]]:
        """Return a 1536-dim embedding vector for *text*, or None on failure."""
        if not text or not text.strip():
            return None
        try:
            response = self.client.embeddings.create(
                model=MODEL, input=text, dimensions=DIMENSIONS
            )
            return response.data[0].embedding
        except OpenAIError as e:
            logger.error(f"Embedding API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None


_instance: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    global _instance
    if _instance is None:
        _instance = EmbeddingGenerator()
    return _instance
