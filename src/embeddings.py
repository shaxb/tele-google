"""
OpenAI Embeddings Generation for Semantic Search
Generates 1536-dimensional vectors using text-embedding-3-small
"""

import time
from typing import List, Optional, Tuple
from loguru import logger
from openai import OpenAI, OpenAIError

from src.config import get_config


class EmbeddingGenerator:
    """
    Generate semantic embeddings for text using OpenAI.
    
    Uses text-embedding-3-small:
    - 1536 dimensions
    - $0.00002 per 1K tokens (~$0.00002 per message)
    - Fast and cost-effective
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        config = get_config()
        self.client = OpenAI(api_key=config.openai.api_key)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
        
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed (typically raw message text)
            
        Returns:
            List of 1536 floats representing the semantic vector
            Returns None on error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
            
        try:
            start_time = time.time()
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract embedding vector
            embedding = response.data[0].embedding
            
            # Get token count for cost tracking
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            logger.debug(
                f"Generated embedding: {len(embedding)} dims, "
                f"{tokens_used} tokens, {processing_time_ms}ms"
            )
            
            return embedding
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error generating embedding: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches (more efficient).
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in one API call (max 2048 for OpenAI)
            
        Returns:
            List of embeddings (same order as input)
            Returns None for texts that failed
        """
        if not texts:
            return []
        
        embeddings: List[Optional[List[float]]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                start_time = time.time()
                
                # Generate embeddings for batch
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions
                )
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
                # Get token count for cost tracking
                tokens_used = response.usage.total_tokens if response.usage else 0
                cost_estimate = (tokens_used / 1000) * 0.00002  # $0.00002 per 1K tokens
                
                logger.info(
                    f"Batch {batch_num}/{total_batches}: "
                    f"{len(batch)} embeddings, "
                    f"{tokens_used} tokens, "
                    f"~${cost_estimate:.6f}, "
                    f"{processing_time_ms}ms"
                )
                
            except OpenAIError as e:
                logger.error(f"OpenAI API error in batch {batch_num}: {e}")
                # Add None for failed batch
                embeddings.extend([None] * len(batch))
            except Exception as e:
                logger.error(f"Unexpected error in batch {batch_num}: {e}")
                embeddings.extend([None] * len(batch))
        
        logger.success(
            f"Generated {sum(1 for e in embeddings if e is not None)}/{len(texts)} embeddings"
        )
        
        return embeddings
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1 (higher = more similar)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimensions")
        
        # Compute dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Compute magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        # Cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity


# Singleton instance
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create EmbeddingGenerator singleton instance."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
