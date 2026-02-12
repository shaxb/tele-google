================================================================================
TELE-GOOGLE: TELEGRAM MARKETPLACE SEARCH ENGINE
================================================================================
Version: 2.0 - Schema-Free Adaptive Architecture
Last Updated: February 1, 2026
Status: Phase 3 Complete - Implementing Adaptive Layer

================================================================================
TABLE OF CONTENTS
================================================================================
1. PROJECT VISION
2. ARCHITECTURE OVERVIEW - ADAPTIVE DESIGN
3. TECH STACK & RATIONALE
4. CORE COMPONENTS
5. DATA FLOW - EMBEDDING-FIRST APPROACH
6. AI PIPELINE DESIGN - UNIVERSAL EXTRACTION
7. DATABASE SCHEMA - SCHEMA-FREE DESIGN
8. IMPLEMENTATION ROADMAP
9. DEVELOPMENT SETUP
10. TESTING STRATEGY
11. SCALING & FUTURE-PROOFING

================================================================================
1. PROJECT VISION
================================================================================

WHAT:
A future-proof, schema-free search engine that indexes Telegram marketplace 
channels and adapts automatically to any content without manual schema updates.

WHY:
Telegram channels post diverse, evolving content (phones, apartments, cars, jobs,
pets, food, services, etc.) in mixed Uzbek/Russian/English. Traditional rigid 
schemas require endless maintenance as new product features emerge (5G, AI chips,
satellite connectivity, etc.). This system adapts automatically.

WHO:
Target users: People in Uzbekistan searching for ANY items across fragmented
marketplace channels, with zero-maintenance backend that never needs schema migrations.

KEY FEATURES:
- Multi-channel indexing (simultaneous monitoring of 100+ channels)
- Natural language search in Uzbek/Russian/English (mixed)
- Semantic understanding via embeddings (not just keyword matching)
- Auto-discovery of new categories and features (no predefined schemas)
- Typo-tolerant search ("ayfon" → "iPhone", "Chilanzor" → "Chilonzor")
- Future-proof: Works for products/features that don't exist yet
- Rich results with images and direct links to original messages

CORE PHILOSOPHY:
❌ DON'T: Predefine rigid schemas that need constant updates
✅ DO: Store embeddings + flexible attributes, let AI discover structure on-the-fly
✅ Zero schema migrations, infinite adaptability

================================================================================
2. ARCHITECTURE OVERVIEW - ADAPTIVE DESIGN
================================================================================

EMBEDDING-FIRST ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────┐
│                     TELEGRAM CHANNELS (Any Topic)                    │
│        (@MalikaBozor, @ToshkentMarket, @PetShopUz, etc.)           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   TELETHON CRAWLER   │
                  │   (Multi-session)    │
                  │   Monitors 100+      │
                  │   channels 24/7      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────────────┐
                  │    UNIVERSAL AI EXTRACTOR    │
                  │  ┌────────────────────────┐  │
                  │  │  GPT-4o-mini           │  │
                  │  │  Discovers structure   │  │
                  │  │  Extracts ANY fields   │  │
                  │  │  No predefined schema  │  │
                  │  └────────────────────────┘  │
                  │  ┌────────────────────────┐  │
                  │  │  OpenAI Embeddings     │  │
                  │  │  text-embedding-3-small│  │
                  │  │  1536-dim vector       │  │
                  │  └────────────────────────┘  │
                  └──────────┬───────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌──────────────────────────┐    ┌──────────────────────┐
│   POSTGRESQL + pgvector  │    │    MEILISEARCH       │
│   - Embeddings (vector)  │    │    - Fast keyword    │
│   - Attributes (JSONB)   │    │    - Typo tolerance  │
│   - Flexible storage     │    │    - Dynamic facets  │
│   - Semantic search      │    │                      │
└──────────────┬───────────┘    └──────────┬───────────┘
               │                           │
               └─────────┬─────────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   HYBRID SEARCH ENGINE   │
              │   Strategy A: Semantic   │
              │   Strategy B: Keyword    │
              │   Strategy C: Hybrid     │
              │   → Merge & Rerank       │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │     AIOGRAM BOT          │
              │   - /search command      │
              │   - Inline queries       │
              │   - Result pagination    │
              └──────────────────────────┘

KEY PRINCIPLES:
1. NO RIGID SCHEMAS: Attributes stored as flexible JSONB
2. EMBEDDING-FIRST: Semantic vectors enable meaning-based search
3. MULTI-STRATEGY: Combine semantic + keyword + filters
4. AUTO-ADAPTIVE: New features/categories discovered automatically
5. FUTURE-PROOF: Zero migrations, works forever
              │   - Query parsing (AI)       │
              │   - Result formatting        │
              │   - Future: Inline mode      │
              └──────────────────────────────┘
                             ▲
                             │
                    ┌────────┴────────┐
                    │     USERS       │
                    └─────────────────┘

================================================================================
3. TECH STACK & RATIONALE
================================================================================

COMPONENT             TECHNOLOGY          WHY CHOSEN
--------------------------------------------------------------------------------
Crawler              Telethon            - Acts as real user (multi-session support)
                                         - Access to any public channel
                                         - Real-time message events

AI Processing        OpenAI GPT-4o-mini  - Cost-effective ($0.15/1M input tokens)
                                         - Handles Uzbek/Russian mix well
                                         - Fast response time

Search Engine        Meilisearch v1.6+   - Built-in typo tolerance
                                         - Fast filtering on nested JSON
                                         - Easy Docker deployment
                                         - Good for 100K-10M documents

Database             PostgreSQL 15+      - Reliable for multi-session tracking
                                         - Better than SQLite for scaling
                                         - JSONB support for flexible data

Bot Framework        Aiogram 3.x         - Modern async Python framework
                                         - Clean API for bot commands
                                         - Inline mode support built-in

Containerization     Docker Desktop      - Meilisearch runs in container
                                         - Easy local development
                                         - Production-ready

Language             Python 3.10+        - Async/await support
                                         - Rich ecosystem for all components
                                         - Type hints for maintainability

================================================================================
4. CORE COMPONENTS
================================================================================

┌─────────────────────────────────────────────────────────────────────┐
│ A. CRAWLER (src/crawler.py)                                         │
├─────────────────────────────────────────────────────────────────────┤
│ Purpose: Listen to Telegram channels and capture new messages       │
│                                                                      │
│ Key Features:                                                        │
│ - Multi-session management (rotate between Telegram accounts)       │
│ - Event-driven message capture                                      │
│ - Image/media download and storage                                  │
│ - Duplicate detection (track last processed message ID)             │
│ - Automatic reconnection on network errors                          │
│                                                                      │
│ Configuration:                                                       │
│ - Session files stored in data/sessions/                            │
│ - Monitored channels defined in config.py                           │
│ - Rate limiting: respect Telegram API limits                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ B. AI PIPELINE (src/ai_parser.py)                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Two-stage processing for consistent field extraction                │
│                                                                      │
│ STAGE 1: ROUTER AI                                                  │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Input:  Raw message text                                        │ │
│ │ Task:   Classify into category + subcategory                    │ │
│ │ Output: {category: "electronics", subcategory: "smartphone"}    │ │
│ │ Cost:   ~100 tokens/request                                     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ STAGE 2: SPECIALIST AI                                              │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Input:  Raw text + category-specific prompt template            │ │
│ │ Task:   Extract structured data using predefined field names    │ │
│ │ Output: {brand: "Apple", model: "iPhone 15", storage: "128GB"}  │ │
│ │ Cost:   ~500 tokens/request                                     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ Why Two Stages:                                                      │
│ ✓ Consistent field naming (each category has strict schema)         │
│ ✓ Cost efficient (specialized prompts are smaller)                  │
│ ✓ Better accuracy (domain-specific context)                         │
│ ✓ Easy to maintain (update one template vs giant prompt)            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ C. CATEGORY SCHEMAS (src/schemas.py)                                │
├─────────────────────────────────────────────────────────────────────┤
│ Predefined field structures for each category/subcategory           │
│                                                                      │
│ ELECTRONICS > SMARTPHONE:                                            │
│   Fields: brand, model, storage, ram, color, condition, price       │
│                                                                      │
│ ELECTRONICS > LAPTOP:                                                │
│   Fields: brand, model, processor, ram, storage, screen_size,       │
│            condition, price                                          │
│                                                                      │
│ REAL_ESTATE > APARTMENT:                                             │
│   Fields: property_type, rooms, floor, total_floors, area_sqm,      │
│            district, price_type, price                               │
│                                                                      │
│ VEHICLES > CAR:                                                      │
│   Fields: brand, model, year, mileage_km, fuel_type, transmission,  │
│            condition, price                                          │
│                                                                      │
│ JOBS > FULL_TIME:                                                    │
│   Fields: position, work_type, experience_years, schedule, salary   │
│                                                                      │
│ Schema Evolution:                                                    │
│ - Start with core categories                                        │
│ - Add new categories/subcategories as discovered                    │
│ - Log unknown fields to extra_attributes for schema updates         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ D. SEARCH ENGINE (src/search.py)                                    │
├─────────────────────────────────────────────────────────────────────┤
│ Meilisearch client wrapper                                          │
│                                                                      │
│ Index Configuration:                                                 │
│ - Filterable: category, subcategory, price, data.* (all nested)     │
│ - Searchable: item, searchable_text, data (all nested)              │
│ - Sortable: price, posted_at                                        │
│ - Typo tolerance: enabled (2 typos max)                             │
│                                                                      │
│ Features:                                                            │
│ - Add/update/delete documents                                       │
│ - Complex filtering (AND/OR/range queries)                          │
│ - Faceted search (category counts)                                  │
│ - Pagination                                                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ E. BOT INTERFACE (src/bot.py)                                       │
├─────────────────────────────────────────────────────────────────────┤
│ Aiogram-based Telegram bot                                          │
│                                                                      │
│ Commands:                                                            │
│ /start   - Welcome message, usage instructions                      │
│ /search  - Main search interface                                    │
│ /help    - Search syntax examples                                   │
│                                                                      │
│ Search Flow:                                                         │
│ 1. User: /search iPhone 15 qora 800$ dan kam                        │
│ 2. Bot uses AI to parse query → filters                             │
│ 3. Query Meilisearch with filters                                   │
│ 4. Format results with images, price, link                          │
│ 5. Send to user (max 10 results, pagination)                        │
│                                                                      │
│ Result Format:                                                       │
│ ┌────────────────────────────────────┐                              │
│ │ 📱 iPhone 15 Pro                   │                              │
│ │ 💰 $750                            │                              │
│ │ 📦 Storage: 256GB                  │                              │
│ │ 🎨 Color: Black                    │                              │
│ │ ✅ Condition: Good                 │                              │
│ │ 🔗 View in channel                 │                              │
│ │ [PHOTO]                            │                              │
│ └────────────────────────────────────┘                              │
│                                                                      │
│ Future: Inline Mode                                                  │
│ - Type @yourbotname iphone 15 in any chat                           │
│ - Get instant results without opening bot                           │
└─────────────────────────────────────────────────────────────────────┘

================================================================================
5. DATA FLOW
================================================================================

INDEXING FLOW (Continuous Background Process):
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  1. New message arrives in Telegram channel                         │
│     ↓                                                                │
│  2. Telethon captures message event                                 │
│     - Extract text, media, metadata                                 │
│     - Check if already processed (duplicate detection)              │
│     ↓                                                                │
│  3. AI Router (Stage 1)                                              │
│     - Classify category/subcategory                                 │
│     - Fast classification (~100ms)                                  │
│     ↓                                                                │
│  4. AI Specialist (Stage 2)                                          │
│     - Load category-specific prompt                                 │
│     - Extract structured fields                                     │
│     - Normalize values                                              │
│     ↓                                                                │
│  5. Build search document:                                           │
│     {                                                                │
│       "id": "channel_username_message_id",                          │
│       "category": "electronics",                                    │
│       "subcategory": "smartphone",                                  │
│       "item": "iPhone 15 Pro",                                      │
│       "data": {                                                     │
│         "brand": "Apple",                                           │
│         "model": "iPhone 15 Pro",                                   │
│         "storage": "256GB",                                         │
│         "color": "black",                                           │
│         "condition": "good"                                         │
│       },                                                            │
│       "price": 750,                                                 │
│       "currency": "USD",                                            │
│       "searchable_text": "iPhone 15 Pro 256GB qora yaxshi holatda", │
│       "images": ["url1", "url2"],                                   │
│       "message_link": "https://t.me/MalikaBozor/12345",            │
│       "channel": "@MalikaBozor",                                    │
│       "posted_at": "2026-01-30T10:30:00Z"                           │
│     }                                                                │
│     ↓                                                                │
│  6. Index to Meilisearch                                             │
│     ↓                                                                │
│  7. Store tracking info in PostgreSQL:                               │
│     - last_processed_message_id per channel                         │
│     - indexing statistics                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

SEARCH FLOW (User-initiated):
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  1. User sends query: "iPhone 15 qora 800$ dan kam"                 │
│     ↓                                                                │
│  2. AI Query Parser                                                  │
│     - Router detects intent category: "electronics"                 │
│     - Specialist extracts filters:                                  │
│       {                                                              │
│         "search_text": "iPhone 15",                                 │
│         "category": "electronics",                                  │
│         "filters": {                                                │
│           "color": "black",                                         │
│           "max_price": 800                                          │
│         }                                                            │
│       }                                                              │
│     ↓                                                                │
│  3. Construct Meilisearch query:                                     │
│     index.search("iPhone 15", {                                     │
│       filter: [                                                     │
│         "category = electronics",                                   │
│         "data.color = black",                                       │
│         "price <= 800"                                              │
│       ],                                                            │
│       sort: ["price:asc"],                                          │
│       limit: 10                                                     │
│     })                                                               │
│     ↓                                                                │
│  4. Meilisearch returns ranked results                               │
│     ↓                                                                │
│  5. Bot formats results with images and links                        │
│     ↓                                                                │
│  6. Send to user (with pagination if >10 results)                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

================================================================================
6. AI PIPELINE DESIGN
================================================================================

ROUTER AI PROMPT TEMPLATE:
```
You are a category classifier for a Uzbek/Russian marketplace.

Analyze the message and return ONLY valid JSON with this structure:
{
  "category": "<category>",
  "subcategory": "<subcategory>",
  "confidence": <0-1>
}

Valid Categories:
1. electronics (smartphones, laptops, tablets, headphones, cameras, accessories)
2. real_estate (apartments, houses, commercial, land)
3. vehicles (cars, motorcycles, bicycles, spare_parts)
4. jobs (full_time, part_time, freelance, internship)
5. services (repair, education, delivery, cleaning, beauty)
6. other (if doesn't fit above)

Examples:
Input: "iPhone 15 Pro, 256GB, qora, zo'r holatda, 900$"
Output: {"category": "electronics", "subcategory": "smartphone", "confidence": 0.95}

Input: "2 xonali kvartira, Chilonzor, 5/9, 50m², 40000$"
Output: {"category": "real_estate", "subcategory": "apartment", "confidence": 0.98}

Input: "Grafik dizayner kerak, masofaviy, 600$"
Output: {"category": "jobs", "subcategory": "full_time", "confidence": 0.85}

================================================================================
6. AI PIPELINE DESIGN - UNIVERSAL EXTRACTION
================================================================================

ADAPTIVE EXTRACTION ARCHITECTURE:

┌──────────────────────────────────────────────────────────────────┐
│ SINGLE-STAGE UNIVERSAL EXTRACTOR (Replaces Router + Specialist) │
├──────────────────────────────────────────────────────────────────┤
│ Model: GPT-4o-mini (JSON mode)                                  │
│ Purpose: Extract ALL information without predefined schemas     │
│ Temperature: 0.2                                                 │
│ Tokens: ~600-800 per message                                    │
│ Cost: ~$0.0001 per message                                      │
└──────────────────────────────────────────────────────────────────┘

UNIVERSAL EXTRACTION PROMPT:
```
You are extracting information from marketplace messages.
Extract ALL structured information - don't limit to predefined fields.

Return ONLY valid JSON:
{
  "attributes": {
    // Extract ANY attributes you find
    // Common: brand, model, size, color, year, condition, etc.
    // Emerging: 5G, AI_chip, gaming, satellite, halal, pet_friendly
    // Normalize when obvious: "qora" → "black", "zo'r" → "excellent"
  },
  "price_min": <number or null>,
  "price_max": <number or null>,
  "currency": "USD|UZS|RUB|null",
  "location": "district/city or null",
  "phone_numbers": ["..."] or null,
  "language": "uz|ru|en|mixed",
  "category_guess": "best guess category"
}

Examples:

Message: "iPhone 15 Pro Max 256GB qora zo'r holatda 950$"
Output: {
  "attributes": {
    "brand": "Apple",
    "model": "iPhone 15 Pro Max",
    "storage": "256GB",
    "color": "black",
    "condition": "excellent"
  },
  "price_min": 950,
  "price_max": null,
  "currency": "USD",
  "category_guess": "electronics"
}

Message: "Gaming laptop ASUS RTX 4090 32GB RAM RGB keyboard 2500$"
Output: {
  "attributes": {
    "brand": "ASUS",
    "GPU": "RTX 4090",
    "RAM": "32GB",
    "gaming": true,
    "RGB_keyboard": true
  },
  "price_min": 2500,
  "currency": "USD",
  "category_guess": "electronics"
}

Message: "it uchun to'shak katta o'lcham yumshoq 50$"
Output: {
  "attributes": {
    "item_type": "bed",
    "animal": "dog",
    "size": "large",
    "material_quality": "soft"
  },
  "price_min": 50,
  "currency": "USD",
  "category_guess": "pets"
}

Now extract from: {message_text}
```

EMBEDDING GENERATION:
```
Model: text-embedding-3-small
Dimensions: 1536
Cost: $0.00002 per message

Purpose: Semantic search (meaning-based, not keyword)
- Enables multilingual search (uz/ru/en)
- Handles synonyms automatically
- Works for ANY content (known or unknown categories)
```

QUERY PARSING (Adaptive):
```
Parse user search query without predefined category assumptions.

Return JSON:
{
  "intent": "buy|sell|compare",
  "main_keywords": ["..."],
  "filters": {
    // ANY attributes user mentions
    // Could be: brand, 5G, gaming, halal, pet-friendly, etc.
  },
  "price_range": {"min": null, "max": null},
  "sort_preference": "price_asc|price_desc|date_desc|relevance"
}

Examples:

Query: "5G telefon 1000$ gacha"
Output: {
  "main_keywords": ["telefon", "5G"],
  "filters": {"5G": true},
  "price_range": {"max": 1000},
  "sort_preference": "price_asc"
}

Query: "gaming laptop kuchli video karta"
Output: {
  "main_keywords": ["laptop", "gaming"],
  "filters": {"gaming": true},
  "sort_preference": "relevance"
}

Query: "halal restoran Chilonzor"
Output: {
  "main_keywords": ["restoran", "halal"],
  "filters": {"halal": true, "location": "Chilonzor"},
  "sort_preference": "relevance"
}
```

================================================================================
7. DATABASE SCHEMA - SCHEMA-FREE DESIGN
================================================================================

PostgreSQL Tables (One-time setup, never needs migration):

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: listings                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Core listing storage with flexible attributes (FUTURE-PROOF)        │
│                                                                      │
│ -- Identity                                                          │
│ id                BIGSERIAL PRIMARY KEY                              │
│ source_channel    TEXT NOT NULL                                      │
│ source_message_id BIGINT NOT NULL                                    │
│                                                                      │
│ -- Content (immutable)                                               │
│ raw_text          TEXT NOT NULL                                      │
│ has_media         BOOLEAN DEFAULT FALSE                              │
│ -- NOTE: No media_urls needed - we share original via t.me links    │
│                                                                      │
│ -- Semantic search (THE CORE!)                                       │
│ embedding         vector(1536) NOT NULL                              │
│                                                                      │
│ -- Flexible attributes (NEVER needs schema changes)                  │
│ attributes        JSONB NOT NULL DEFAULT '{}'                        │
│ -- Can contain ANYTHING:                                             │
│ -- 2024: {"brand": "Apple", "model": "iPhone 13"}                    │
│ -- 2025: {"brand": "Apple", "5G": true, "model": "iPhone 15"}       │
│ -- 2026: {"brand": "Apple", "AI_chip": "A18", "satellite": true}    │
│ -- 2027+: {whatever_new_features_exist}                              │
│                                                                      │
│ -- Common fast filters (auto-extracted)                              │
│ price_min         NUMERIC                                            │
│ price_max         NUMERIC                                            │
│ currency          TEXT                                               │
│ location          TEXT                                               │
│ phone_numbers     TEXT[]                                             │
│                                                                      │
│ -- Metadata                                                          │
│ language          TEXT                  -- uz, ru, en, mixed         │
│ category_guess    TEXT                  -- Auto-discovered           │
│ created_at        TIMESTAMPTZ DEFAULT NOW()                          │
│ indexed_at        TIMESTAMPTZ DEFAULT NOW()                          │
│                                                                      │
│ UNIQUE(source_channel, source_message_id)                            │
└─────────────────────────────────────────────────────────────────────┘

INDEXES (One-time setup):
```sql
-- Semantic search (pgvector)
CREATE INDEX idx_embedding ON listings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Dynamic attribute search
CREATE INDEX idx_attributes_gin ON listings 
    USING gin(attributes jsonb_path_ops);

-- Fast price filtering
CREATE INDEX idx_price ON listings (price_min, price_max) 
    WHERE price_min IS NOT NULL;

-- Recency sorting
CREATE INDEX idx_created ON listings (created_at DESC);

-- Location filtering
CREATE INDEX idx_location ON listings (location) 
    WHERE location IS NOT NULL;
```

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: telegram_sessions                                             │
├─────────────────────────────────────────────────────────────────────┤
│ Manages multiple Telegram userbot sessions                          │
│                                                                      │
│ id                SERIAL PRIMARY KEY                                 │
│ session_name      VARCHAR(100) UNIQUE NOT NULL                       │
│ phone_number      VARCHAR(20) NOT NULL                               │
│ api_id            INTEGER NOT NULL                                   │
│ api_hash          VARCHAR(100) NOT NULL                              │
│ is_active         BOOLEAN DEFAULT true                               │
│ last_used_at      TIMESTAMP                                          │
│ created_at        TIMESTAMP DEFAULT NOW()                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: monitored_channels                                            │
├─────────────────────────────────────────────────────────────────────┤
│ Tracks which channels are being monitored                            │
│                                                                      │
│ id                SERIAL PRIMARY KEY                                 │
│ username          VARCHAR(100) UNIQUE NOT NULL                       │
│ title             VARCHAR(255)                                       │
│ is_active         BOOLEAN DEFAULT true                               │
│ last_message_id   BIGINT DEFAULT 0                                   │
│ total_indexed     INTEGER DEFAULT 0                                  │
│ session_id        INTEGER REFERENCES telegram_sessions(id)           │
│ added_at          TIMESTAMP DEFAULT NOW()                            │
│ last_scraped_at   TIMESTAMP                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: search_analytics                                              │
├─────────────────────────────────────────────────────────────────────┤
│ Tracks user searches for analytics and future learning              │
│                                                                      │
│ id                SERIAL PRIMARY KEY                                 │
│ user_id           BIGINT NOT NULL                                    │
│ query_text        TEXT NOT NULL                                      │
│ filters_applied   JSONB                                              │
│ results_count     INTEGER                                            │
│ clicked_result_id BIGINT                                             │
│ searched_at       TIMESTAMP DEFAULT NOW()                            │
│ response_time_ms  INTEGER                                            │
└─────────────────────────────────────────────────────────────────────┘

MEILISEARCH INDEX STRUCTURE (Flexible):

Index name: "listings"

Document structure:
{
  "id": "string",                    // Format: {channel}_{message_id}
  "raw_text": "string",              // Original message
  "attributes": {                    // FLEXIBLE - any fields!
    // Auto-discovered attributes
    // 2024: "brand", "model", "storage"
    // 2025+: "5G", "AI_chip", "gaming", "halal", etc.
  },
  "price_min": number,
  "price_max": number,
  "currency": "string",
  "location": "string",
  "category_guess": "string",
  "created_at": timestamp,
  "source_channel": "string"
}

Index settings:
```json
{
  "searchableAttributes": [
    "raw_text",
    "attributes"
  ],
  "filterableAttributes": [
    "price_min",
    "price_max",
    "currency",
    "location",
    "category_guess",
    "created_at",
    "attributes"
  ],
  "sortableAttributes": [
    "price_min",
    "created_at"
  ],
  "typoTolerance": {
    "enabled": true,
    "minWordSizeForTypos": {
      "oneTypo": 4,
      "twoTypos": 8
    }
  }
}
```

================================================================================
8. IMPLEMENTATION ROADMAP
================================================================================

STATUS LEGEND:
[ ] Not Started
[~] In Progress  
[✓] Completed
[D] Deprecated (removed)

PHASE 1: PROJECT SETUP
├─ [✓] Architecture finalized
├─ [✓] Tech stack decided
├─ [✓] Create project structure
│   ├─ [✓] Initialize Git repository
│   ├─ [✓] Create directory structure
│   ├─ [✓] Setup .env template
│   └─ [✓] Create requirements.txt
├─ [✓] Docker setup
│   ├─ [✓] Create docker-compose.yml (Meilisearch + PostgreSQL)
│   ├─ [✓] Test Meilisearch connection
│   └─ [✓] Test PostgreSQL connection
└─ [✓] Configuration management
    ├─ [✓] Create src/config.py
    └─ [✓] Environment validation

PHASE 2: DATABASE LAYER (SCHEMA-FREE)
├─ [✓] PostgreSQL setup
│   ├─ [✓] Create initial migrations
│   ├─ [D] Old rigid schema (4 tables) - DEPRECATED
│   └─ [~] New schema-free design (listings table with JSONB)
├─ [✓] pgvector extension
│   ├─ [~] Install pgvector in PostgreSQL
│   ├─ [~] Create vector indexes
│   └─ [~] Test embedding storage/retrieval
├─ [✓] Meilisearch setup
│   ├─ [✓] Initialize index
│   ├─ [~] Configure for dynamic attributes
│   └─ [~] Test flexible attribute search
└─ [~] Database utilities
    ├─ [✓] Connection pooling
    └─ [~] Update models for JSONB attributes

PHASE 3: ADAPTIVE AI PIPELINE
├─ [✓] Deprecated rigid schemas (src/schemas.py removed)
├─ [✓] Universal Extractor (src/ai_parser.py)
│   ├─ [✓] Write universal extraction prompt
│   ├─ [✓] Implement adaptive extraction function
│   ├─ [✓] Auto-normalize common values
│   └─ [✓] Test with diverse messages (9/10 passed)
├─ [✓] Embedding Generation (src/embeddings.py)
│   ├─ [✓] Integrate OpenAI embeddings API
│   ├─ [✓] Batch processing for efficiency
│   └─ [✓] Test semantic similarity
├─ [✓] Adaptive Query Parser (src/ai_parser.py)
│   ├─ [✓] Write flexible query parsing prompt
│   ├─ [✓] Implement dynamic filter extraction
│   ├─ [✓] Handle Uzbek/Russian comparison phrases
│   └─ [✓] Test with diverse queries (5/5 passed)
└─ [✓] Hybrid Search Engine (src/search_engine.py)
    ├─ [✓] Strategy A: Semantic vector search
    ├─ [✓] Strategy B: Keyword + filters (Meilisearch)
    ├─ [✓] Strategy C: Hybrid combination
    ├─ [✓] Result merging and deduplication
    └─ [✓] Reranking logic

PHASE 4: CRAWLER
├─ [✓] Telethon setup (src/crawler.py)
│   ├─ [✓] Session management (multi-account)
│   ├─ [✓] Channel joining logic
│   └─ [✓] Event handler for new messages
├─ [✓] Message processing
│   ├─ [✓] Text extraction
│   ├─ [✓] Media detection (check has_media flag)
│   ├─ [✓] Metadata extraction (timestamp, message_id)
│   ├─ [✓] Duplicate detection
│   └─ [✓] NOTE: No media download needed - we share original Telegram messages
├─ [✓] Integration with AI pipeline
│   ├─ [✓] Universal Extractor (adaptive extraction)
│   ├─ [✓] Embedding generation (semantic search)
│   └─ [✓] Error handling (retry logic)
├─ [✓] Indexing integration
│   ├─ [✓] Build Meilisearch document
│   ├─ [✓] Index to Meilisearch
│   └─ [✓] Store in PostgreSQL with message link
└─ [✓] Management scripts
    ├─ [✓] Add/remove channels (manage_crawler.py)
    ├─ [✓] Backfill historical messages
    └─ [✓] Multi-session management

PHASE 5: SEARCH LAYER
├─ [ ] Meilisearch wrapper (src/search.py)
│   ├─ [ ] Search function with filters
│   ├─ [ ] Pagination support
│   ├─ [ ] Faceted search (category counts)
│   └─ [ ] Error handling
└─ [ ] Query optimization
    ├─ [ ] Test typo tolerance
    ├─ [ ] Test filter combinations
    └─ [ ] Performance benchmarking

PHASE 6: BOT INTERFACE
├─ [ ] Aiogram setup (src/bot.py)
│   ├─ [ ] Bot initialization
│   ├─ [ ] Command handlers (/start, /help, /search)
│   └─ [ ] Message handlers
├─ [ ] Search implementation
│   ├─ [ ] Parse user query with AI
│   ├─ [ ] Query Meilisearch
│   ├─ [ ] Format results (with images)
│   └─ [ ] Pagination (next/previous buttons)
└─ [ ] User experience
    ├─ [ ] Rich result formatting
    ├─ [ ] Inline keyboard for actions
    └─ [ ] Error messages (no results, invalid query)

PHASE 7: TESTING & OPTIMIZATION
├─ [ ] Unit tests
│   ├─ [ ] AI parser tests
│   ├─ [ ] Search function tests
│   └─ [ ] Database operation tests
├─ [ ] Integration tests
│   ├─ [ ] End-to-end indexing flow
│   └─ [ ] End-to-end search flow
├─ [ ] Performance optimization
│   ├─ [ ] AI token usage analysis
│   ├─ [ ] Database query optimization
│   └─ [ ] Meilisearch index tuning
└─ [ ] Error handling & logging
    ├─ [ ] Comprehensive error handling
    ├─ [ ] Logging setup (structured logs)
    └─ [ ] Monitoring setup

PHASE 8: DEPLOYMENT
├─ [ ] Production configuration
│   ├─ [ ] Environment variables
│   ├─ [ ] Secrets management
│   └─ [ ] Docker Compose for production
├─ [ ] Process management
│   ├─ [ ] Systemd service files / Supervisor
│   ├─ [ ] Auto-restart on failure
│   └─ [ ] Graceful shutdown
└─ [ ] Monitoring & maintenance
    ├─ [ ] Health check endpoints
    ├─ [ ] Analytics dashboard
    └─ [ ] Backup strategy

PHASE 9: FUTURE ENHANCEMENTS (Post-MVP)
├─ [ ] Inline mode for bot
├─ [ ] Admin panel for managing channels
├─ [ ] Notification system (price drops, new items)
├─ [ ] User favorites/saved searches
├─ [ ] Vector search for semantic similarity
└─ [ ] Multi-language support expansion

================================================================================
9. DEVELOPMENT SETUP
================================================================================

PREREQUISITES:
- Python 3.10 or higher
- Docker Desktop (for Windows)
- Telegram account (for userbot)
- OpenAI API key
- PostgreSQL (via Docker)

STEP-BY-STEP SETUP:

1. CLONE AND ENVIRONMENT
   ```bash
   cd c:\projects\tele-google
   python -m venv venv
   venv\Scripts\activate
   ```

2. INSTALL DEPENDENCIES
   ```bash
   pip install -r requirements.txt
   ```

3. ENVIRONMENT VARIABLES (.env)
   ```
   # Telegram (get from https://my.telegram.org)
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_PHONE=+998901234567
   
   # OpenAI
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   
   # Meilisearch
   MEILI_HOST=http://localhost:7700
   MEILI_MASTER_KEY=masterKey
   MEILI_INDEX=marketplace
   
   # PostgreSQL
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=tele_google
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   
   # Bot
   BOT_TOKEN=your_bot_token_from_botfather
   
   # Monitoring Channels (comma-separated)
   CHANNELS=@MalikaBozor,@ToshkentMarket
   ```

4. START DOCKER SERVICES
   ```bash
   docker-compose up -d
   ```

5. INITIALIZE DATABASE
   ```bash
   python scripts/init_db.py
   ```

6. RUN CRAWLER (Background)
   ```bash
   python src/crawler.py
   ```

7. RUN BOT (Foreground)
   ```bash
   python src/bot.py
   ```

FILE STRUCTURE:
```
tele-google/
├── .env                          # Environment variables (gitignored)
├── .gitignore                   
├── docker-compose.yml            # Docker services (Meilisearch + PostgreSQL)
├── requirements.txt              # Python dependencies
├── README.md                     # User-facing documentation
├── PROJECT_GUIDE.md              # This file (development guide)
│
├── data/                         # Persistent data (gitignored)
│   ├── sessions/                 # Telethon session files
│   ├── meili_data/               # Meilisearch index data
│   └── images/                   # Downloaded message images
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration loader
│   ├── schemas.py                # Category schemas and field definitions
│   ├── prompts.py                # AI prompt templates
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy models
│   │   └── connection.py         # Database connection management
│   │
│   ├── ai_parser.py              # AI pipeline (Router + Specialist + Query)
│   ├── crawler.py                # Telethon crawler (main listener)
│   ├── search.py                 # Meilisearch wrapper
│   ├── bot.py                    # Aiogram bot (entry point)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Logging configuration
│       └── helpers.py            # Common utilities
│
├── scripts/
│   ├── init_db.py                # Database initialization
│   ├── test_ai_parser.py         # Test AI extraction
│   └── backfill_channel.py       # Manually index old messages
│
└── tests/
    ├── test_ai_parser.py
    ├── test_search.py
    └── test_crawler.py
```

================================================================================
10. TESTING STRATEGY
================================================================================

UNIT TESTS:
┌─────────────────────────────────────────────────────────────────────┐
│ Component         Test Cases                                        │
├─────────────────────────────────────────────────────────────────────┤
│ AI Router        - Classification accuracy (20+ sample messages)    │
│                  - Confidence threshold handling                    │
│                  - Unknown category handling                        │
│                                                                      │
│ AI Specialist    - Field extraction accuracy per category           │
│                  - Value normalization (colors, conditions)         │
│                  - Missing field handling (null values)             │
│                                                                      │
│ Query Parser     - Filter extraction from Uzbek queries             │
│                  - Price range parsing ("dan kam", "gacha")         │
│                  - Multiple filters in one query                    │
│                                                                      │
│ Search Engine    - Typo tolerance ("ayfon" → "iPhone")              │
│                  - Filter combinations (AND/OR)                     │
│                  - Sorting and pagination                           │
│                                                                      │
│ Database         - CRUD operations                                  │
│                  - Duplicate detection                              │
│                  - Transaction handling                             │
└─────────────────────────────────────────────────────────────────────┘

INTEGRATION TESTS:
- Full indexing pipeline (message → AI → Meilisearch)
- Full search pipeline (query → AI → Meilisearch → results)
- Multi-session crawler behavior
- Error recovery (API failures, network errors)

PERFORMANCE BENCHMARKS:
- AI parsing speed (target: <500ms per message)
- Search response time (target: <100ms)
- Indexing throughput (target: 100 messages/minute)
- Database query performance

TEST DATA:
Create test_messages.json with 50+ real-world examples:
- 10 electronics (varied brands, conditions)
- 10 real estate (different districts, sizes)
- 10 vehicles
- 10 jobs
- 10 edge cases (typos, mixed languages, incomplete info)

================================================================================
11. FUTURE ENHANCEMENTS
================================================================================

POST-MVP FEATURES (Priority Order):

1. INLINE MODE
   - Allow users to search from any chat: @yourbot iphone 15
   - Requires: inline query handler, result article formatting
   - User benefit: Faster access, share results in group chats

2. ADMIN PANEL
   - Web interface to manage monitored channels
   - View indexing statistics
   - Manual re-indexing triggers
   - Category schema editor

3. PRICE DROP NOTIFICATIONS
   - Users subscribe to specific searches
   - Get notified when matching item appears
   - Price tracking for items they're watching

4. SAVED SEARCHES & FAVORITES
   - Users save frequent searches
   - Bookmark specific items
   - History of searches

5. SEMANTIC SEARCH (Vector Similarity)
   - Use embeddings for "find similar items"
   - Better handling of vague queries
   - Recommendation system

6. MULTI-LANGUAGE EXPANSION
   - Add English language support
   - Turkish language support
   - Auto-detect query language

7. IMAGE SEARCH
   - Upload photo, find similar items
   - Vision AI for product recognition

8. SELLER REPUTATION SYSTEM
   - Track seller activity across channels
   - Review system
   - Trust score

================================================================================
DECISION LOG
================================================================================

DATE         DECISION                                    RATIONALE
--------------------------------------------------------------------------------
2026-01-30   Multi-session Telethon approach            Scale to many channels
2026-01-30   PostgreSQL over SQLite                     Better for scaling
2026-01-30   Two-stage AI pipeline                      Consistent fields, lower cost
2026-01-30   Meilisearch over PostgreSQL FTS            Better typo tolerance
2026-01-30   Inline mode as future enhancement          MVP focus on core search
2026-01-30   Flexible data field with controlled vocab  Balance flexibility/consistency

================================================================================
CONTACTS & RESOURCES
================================================================================

Documentation:
- Telethon: https://docs.telethon.dev/
- Aiogram: https://docs.aiogram.dev/
- Meilisearch: https://www.meilisearch.com/docs
- OpenAI API: https://platform.openai.com/docs

Telegram Resources:
- Get API credentials: https://my.telegram.org/apps
- BotFather: @BotFather (create bot, get token)

Development:
- Repository: (to be created)
- Issue Tracker: (to be created)
- CI/CD: (to be set up)

================================================================================
END OF PROJECT GUIDE
================================================================================

This document should be updated as the project evolves.
When new architectural decisions are made, update the DECISION LOG section.
When phases are completed, update the checkboxes in IMPLEMENTATION ROADMAP.

Version History:
- v1.0 (2026-01-30): Initial architecture and design document
