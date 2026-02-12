# AI Pipeline - Simple listing check + search reranking
# Two functions: is_listing() and rerank()

import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from openai import OpenAI, OpenAIError

from src.config import get_config
from src.prompts import (
    LISTING_CHECK_PROMPT,
    RERANK_PROMPT,
    create_listing_check_prompt,
    create_rerank_prompt,
)


class AIParser:
    
    def __init__(self):
        config = get_config()
        self.client = OpenAI(api_key=config.openai.api_key)
        self.model = config.openai.model
        
    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """Call OpenAI API and return parsed JSON response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return None
            
            parsed = json.loads(content)
            
            # Add token usage
            if response.usage:
                parsed["_tokens"] = response.usage.prompt_tokens + response.usage.completion_tokens
            
            return parsed
            
        except (OpenAIError, json.JSONDecodeError) as e:
            logger.error(f"OpenAI error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def is_listing(self, message_text: str) -> bool:
        """Check if a message is a marketplace listing. Returns True/False."""
        start = time.time()
        
        result = self._call_openai(
            system_prompt=LISTING_CHECK_PROMPT,
            user_prompt=create_listing_check_prompt(message_text),
            temperature=0.1
        )
        
        ms = int((time.time() - start) * 1000)
        tokens = result.get("_tokens", 0) if result else 0
        is_listing = result.get("is_listing", False) if result else False
        
        if is_listing:
            logger.info(f"✅ Listing detected ({tokens} tokens, {ms}ms): {message_text[:50]}...")
        else:
            logger.info(f"⏭️ Not a listing ({tokens} tokens, {ms}ms): {message_text[:50]}...")
        
        return is_listing
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[int]:
        """Rerank candidates by relevance to query. Returns ordered list of indices."""
        start = time.time()
        
        if not candidates:
            return []
        
        result = self._call_openai(
            system_prompt=RERANK_PROMPT,
            user_prompt=create_rerank_prompt(query, candidates),
            temperature=0.2
        )
        
        ms = int((time.time() - start) * 1000)
        tokens = result.get("_tokens", 0) if result else 0
        
        if not result:
            logger.warning(f"Rerank failed for '{query}', returning first 5")
            return list(range(min(5, len(candidates))))
        
        indices = result.get("relevant_indices", [])
        reasoning = result.get("reasoning", "")
        
        # Validate indices
        valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < len(candidates)]
        
        logger.info(
            f"Rerank: '{query}' → {len(valid_indices)} relevant "
            f"({tokens} tokens, {ms}ms) | {reasoning}"
        )
        
        return valid_indices


# Singleton
_ai_parser: Optional[AIParser] = None

def get_ai_parser() -> AIParser:
    global _ai_parser
    if _ai_parser is None:
        _ai_parser = AIParser()
    return _ai_parser
