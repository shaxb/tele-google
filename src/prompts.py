"""AI prompts — listing classification, metadata extraction, and search reranking."""

LISTING_CHECK_PROMPT = """You classify Telegram messages from Uzbekistan marketplace channels.

TASK: Determine if the message is a marketplace listing. If it IS a listing, extract structured metadata.

A MARKETPLACE LISTING is a message where someone is selling, renting, or offering a specific item/service with details (price, specs, contact info, etc).

NOT a listing:
- Greetings, thank you messages ("Rahmat!", "Salom!")
- "Sold" notifications ("sotildi", "продано")
- Channel rules, announcements, ads for other channels
- General discussions, questions, memes
- Job postings that are just ads without specific details

If it IS a listing, extract metadata using these EXACT field names for universal fields:
- "price": numeric value only (no formatting). If multiple prices, use the main/primary one.
- "currency": one of "USD", "UZS", "EUR", or null if unclear. Hint: "$" = USD, "сўм"/"so'm" = UZS.
- "category": one of "car", "phone", "apartment", "electronics", "clothing", "furniture", "services", "other"
- "title": short normalized item name in original language, e.g. "iPhone 13 128GB", "Gentra 2022", "3-xonali kvartira"
- "condition": "new", "used", or null if not mentioned

Also extract any ADDITIONAL item-specific fields you find, using intuitive English snake_case names:
- For phones: "brand", "model", "storage_gb", "ram_gb", "color"
- For cars: "brand", "model", "year", "mileage_km", "fuel_type", "transmission", "color"
- For apartments: "rooms", "floor", "total_floors", "area_sqm", "district", "city"
- For any item: add relevant fields as you see them. Use common sense naming.

Respond with ONLY valid JSON:
- If NOT a listing: {"is_listing": false}
- If IS a listing: {"is_listing": true, "metadata": {"price": 12000, "currency": "USD", "category": "car", "title": "Gentra 2022", "condition": "used", "year": 2022, "mileage_km": 45000, ...}}"""


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
    """Build user prompt for AI reranking."""
    lines = [f"[{i}] {c.get('raw_text', '')[:300]}" for i, c in enumerate(candidates)]
    return f"User query: {query}\n\nCandidate listings:\n" + "\n".join(lines)
