"""
AI Prompts for Tele-Google
Two simple prompts:
1. LISTING_CHECK - Is this a marketplace listing? (yes/no)
2. RERANK - Given candidates, pick the most relevant ones for the user query
"""


# ============================================================================
# LISTING CHECK PROMPT - Simple yes/no classification
# ============================================================================

LISTING_CHECK_PROMPT = """You classify Telegram messages as marketplace listings or not.

A MARKETPLACE LISTING is a message where someone is selling, renting, or offering a specific item/service with details (price, specs, contact info, etc).

NOT a listing:
- Greetings, thank you messages ("Rahmat!", "Salom!")
- "Sold" notifications ("sotildi", "продано")
- Channel rules, announcements, ads for other channels
- General discussions, questions, memes
- Job postings that are just ads without specific details

Respond with ONLY valid JSON:
{"is_listing": true} or {"is_listing": false}"""


# ============================================================================
# RERANK PROMPT - Pick most relevant listings for user query
# ============================================================================

RERANK_PROMPT = """You are a marketplace search assistant for Uzbekistan.
Users search in Uzbek, Russian, English, or mixed languages.

Given a user's search query and candidate listings, rank them by relevance.

CRITICAL MATCHING RULES:
1. **Semantic Matching** - Match on MEANING, not exact keywords:
   - "kvartira" = "uy" = "xonadon" = apartment/house
   - "mashina" = "moshina" = "avto" = "car"
   - "telefon" = "tel" = "phone" = "ayfon"

2. **Price Understanding**:
   - "dan kam" / "gacha" = less than / up to
   - "dan ko'p" / "dan yuqori" = more than
   - Match currency context (so'm, $, USD)
   - If user mentions price, prioritize listings in that range

3. **Typo Tolerance**:
   - "laceti" = "Lacetti" = "lasetti"
   - "ayfon" = "iPhone" = "iphone"
   - "jentra" = "Gentra"

4. **Category Intent**:
   - If user specifies category (mashina, kvartira, telefon), STRONGLY prioritize that
   - But still allow partial matches if nothing in exact category

5. **Specificity Bonus**:
   - If user mentions model/brand (iPhone 13, Lacetti 2024), exact matches rank higher
   - But also include close matches (iPhone 12, iPhone 14)

6. **Relevance Tiers**:
   - PERFECT: Exact match on category, brand, model, price range
   - GOOD: Matches category + most attributes
   - OKAY: Same category but different specs
   - WEAK: Related but wrong category (still return if <5 good matches)

Respond with ONLY valid JSON:
{
  "relevant_indices": [0, 3, 7],
  "reasoning": "brief explanation of ranking"
}

- Return indices (0-based) ordered by relevance (most relevant FIRST)
- Return UP TO 5 results (fewer if not enough relevant matches)
- If NOTHING is relevant, return: {"relevant_indices": [], "reasoning": "no matches"}"""


def create_listing_check_prompt(message_text: str) -> str:
    """Create user prompt for listing classification."""
    return f"Is this a marketplace listing?\n\n{message_text}"


def create_rerank_prompt(query: str, candidates: list[dict]) -> str:
    """Create user prompt for AI reranking.
    
    Args:
        query: User's search query
        candidates: List of candidate listings with index and raw_text
    """
    candidates_text = ""
    for i, c in enumerate(candidates):
        text_preview = c.get("raw_text", "")[:300]
        candidates_text += f"\n[{i}] {text_preview}\n"
    
    return (
        f"User query: {query}\n\n"
        f"Candidate listings:\n{candidates_text}"
    )
