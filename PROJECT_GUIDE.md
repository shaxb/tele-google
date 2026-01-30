================================================================================
TELE-GOOGLE: TELEGRAM MARKETPLACE SEARCH ENGINE
================================================================================
Version: 1.0
Last Updated: January 30, 2026
Status: Architecture Finalized - Implementation Pending

================================================================================
TABLE OF CONTENTS
================================================================================
1. PROJECT VISION
2. ARCHITECTURE OVERVIEW
3. TECH STACK & RATIONALE
4. CORE COMPONENTS
5. DATA FLOW
6. AI PIPELINE DESIGN
7. DATABASE SCHEMA
8. IMPLEMENTATION ROADMAP
9. DEVELOPMENT SETUP
10. TESTING STRATEGY
11. FUTURE ENHANCEMENTS

================================================================================
1. PROJECT VISION
================================================================================

WHAT:
A real-time search engine that indexes public Telegram marketplace channels
and makes their content searchable through a Telegram bot.

WHY:
Telegram channels post unstructured marketplace messages in mixed Uzbek/Russian.
Users can't search across multiple channels efficiently. This solves that.

WHO:
Target users: People in Uzbekistan searching for items (phones, apartments, jobs)
across fragmented marketplace channels.

KEY FEATURES:
- Multi-channel indexing (simultaneous monitoring)
- Natural language search in Uzbek/Russian
- Typo-tolerant search ("ayfon" → "iPhone")
- Category-aware filtering (price ranges, conditions, locations)
- Rich results with images and direct links to original messages

================================================================================
2. ARCHITECTURE OVERVIEW
================================================================================

┌─────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CHANNELS                             │
│                 (@MalikaBozor, @ToshkentMarket, etc.)               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   TELETHON CRAWLER   │
                  │   (Multi-session)    │
                  │   Listens to new     │
                  │   messages 24/7      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    AI PIPELINE       │
                  │  ┌────────────────┐  │
                  │  │ 1. ROUTER AI   │  │ ← Classifies category
                  │  │ (GPT-4o-mini)  │  │
                  │  └────────┬───────┘  │
                  │           │          │
                  │           ▼          │
                  │  ┌────────────────┐  │
                  │  │ 2. SPECIALIST  │  │ ← Extracts structured data
                  │  │    AI          │  │
                  │  │ (GPT-4o-mini)  │  │
                  │  └────────────────┘  │
                  └──────────┬───────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │       MEILISEARCH            │
              │   (Docker Container)         │
              │   - Typo tolerance           │
              │   - Fast filtering           │
              │   - Multi-field search       │
              └──────────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   POSTGRESQL DB      │
                  │   - Session tracking │
                  │   - Message state    │
                  │   - Analytics        │
                  └──────────────────────┘
                             ▲
                             │
                             │
              ┌──────────────┴───────────────┐
              │      AIOGRAM BOT             │
              │   - /search command          │
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

Now classify this message:
{message_text}
```

SPECIALIST AI PROMPT TEMPLATES (Category-Specific):

┌─────────────────────────────────────────────────────────────────────┐
│ ELECTRONICS > SMARTPHONE                                             │
├─────────────────────────────────────────────────────────────────────┤
│ Extract smartphone details using THESE EXACT field names:            │
│                                                                      │
│ Required fields:                                                     │
│ - brand: Apple, Samsung, Xiaomi, Oppo, Vivo, etc.                   │
│ - model: iPhone 15, Galaxy S24, Redmi Note 13, etc.                 │
│                                                                      │
│ Optional fields (use null if not mentioned):                         │
│ - storage: 64GB, 128GB, 256GB, 512GB, 1TB                           │
│ - ram: 4GB, 6GB, 8GB, 12GB, 16GB                                    │
│ - color: black, white, blue, red, green, gray, gold, etc.           │
│ - condition: new, excellent, good, fair, poor                       │
│ - price: number only (extract from $, сум, so'm)                    │
│ - currency: USD, UZS                                                 │
│                                                                      │
│ Normalization rules:                                                 │
│ - "zo'r holatda", "a'lo" → excellent                                │
│ - "yaxshi", "normal" → good                                         │
│ - "qora" → black, "oq" → white                                      │
│                                                                      │
│ Return ONLY valid JSON.                                              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ REAL_ESTATE > APARTMENT                                              │
├─────────────────────────────────────────────────────────────────────┤
│ Extract apartment details using THESE EXACT field names:             │
│                                                                      │
│ Required fields:                                                     │
│ - property_type: apartment, studio, penthouse                       │
│ - rooms: number (1, 2, 3, 4, 5+)                                    │
│                                                                      │
│ Optional fields:                                                     │
│ - floor: number (extract from "5/9" → 5)                            │
│ - total_floors: number (extract from "5/9" → 9)                     │
│ - area_sqm: number (square meters)                                  │
│ - district: Chilonzor, Yunusobod, Sergeli, Mirzo-Ulugbek, etc.      │
│ - price_type: sale, monthly_rent, daily_rent                        │
│ - price: number only                                                 │
│ - currency: USD, UZS                                                 │
│ - has_furniture: true/false                                          │
│ - has_parking: true/false                                            │
│                                                                      │
│ Normalization:                                                       │
│ - "sotiladi" → sale                                                 │
│ - "ijaraga", "ijara" → monthly_rent                                 │
│ - "kunlik" → daily_rent                                             │
│                                                                      │
│ Return ONLY valid JSON.                                              │
└─────────────────────────────────────────────────────────────────────┘

(Additional templates for other categories stored in src/prompts/)

QUERY PARSING (User Search Intent):
```
You are a search query parser for a marketplace.

User is searching in category: {detected_category}

Extract search intent and filters from their query.

Return ONLY valid JSON:
{
  "search_text": "<main search terms>",
  "filters": {
    "<field_name>": <value>,
    "min_<field>": <number>,
    "max_<field>": <number>
  },
  "sort_by": "price_asc|price_desc|date_desc",
  "intent": "buy|sell|compare"
}

Understanding Uzbek comparison phrases:
- "dan kam", "dan arzon", "gacha" → max_price
- "dan ko'p", "dan baland", "dan yuqori" → min_price
- "orasida" → price range (both min and max)

Example:
User: "iPhone 15 qora 128GB 800$ dan kam"
Output: {
  "search_text": "iPhone 15",
  "filters": {
    "color": "black",
    "storage": "128GB",
    "max_price": 800
  },
  "sort_by": "price_asc",
  "intent": "buy"
}

Now parse: {user_query}
```

================================================================================
7. DATABASE SCHEMA
================================================================================

PostgreSQL Tables:

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
│ username          VARCHAR(100) UNIQUE NOT NULL  (@MalikaBozor)       │
│ title             VARCHAR(255)                                       │
│ is_active         BOOLEAN DEFAULT true                               │
│ last_message_id   BIGINT DEFAULT 0  -- For duplicate detection       │
│ total_indexed     INTEGER DEFAULT 0                                  │
│ session_id        INTEGER REFERENCES telegram_sessions(id)           │
│ added_at          TIMESTAMP DEFAULT NOW()                            │
│ last_scraped_at   TIMESTAMP                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: indexing_log                                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Tracks indexing operations for debugging and analytics              │
│                                                                      │
│ id                SERIAL PRIMARY KEY                                 │
│ channel_id        INTEGER REFERENCES monitored_channels(id)          │
│ message_id        BIGINT NOT NULL                                    │
│ document_id       VARCHAR(255) UNIQUE  -- Meilisearch doc ID         │
│ category          VARCHAR(50)                                        │
│ subcategory       VARCHAR(50)                                        │
│ indexed_at        TIMESTAMP DEFAULT NOW()                            │
│ router_tokens     INTEGER  -- AI cost tracking                       │
│ specialist_tokens INTEGER                                            │
│ processing_time_ms INTEGER                                           │
│ status            VARCHAR(20)  -- success, failed, skipped           │
│ error_message     TEXT                                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TABLE: search_analytics                                              │
├─────────────────────────────────────────────────────────────────────┤
│ Tracks user searches for improvement and analytics                  │
│                                                                      │
│ id                SERIAL PRIMARY KEY                                 │
│ user_id           BIGINT NOT NULL  -- Telegram user ID               │
│ query_text        TEXT NOT NULL                                      │
│ detected_category VARCHAR(50)                                        │
│ filters_applied   JSONB  -- Extracted filters                        │
│ results_count     INTEGER                                            │
│ clicked_result    VARCHAR(255)  -- Which result they clicked         │
│ searched_at       TIMESTAMP DEFAULT NOW()                            │
│ response_time_ms  INTEGER                                            │
└─────────────────────────────────────────────────────────────────────┘

MEILISEARCH INDEX STRUCTURE:

Index name: "marketplace"

Document structure:
{
  "id": "string",                    // Format: {channel}_{message_id}
  "category": "string",              // electronics, real_estate, etc.
  "subcategory": "string",           // smartphone, apartment, etc.
  "item": "string",                  // Human-readable item name
  
  "data": {                          // Flexible nested object
    // Category-specific fields with consistent naming
    // Examples:
    // Electronics: {brand, model, storage, ram, color, condition}
    // Real Estate: {rooms, floor, area_sqm, district}
  },
  
  "price": number,                   // Normalized to single currency
  "currency": "string",              // USD, UZS
  
  "searchable_text": "string",       // All searchable content combined
  
  "images": ["url1", "url2"],        // Array of image URLs
  "message_link": "string",          // https://t.me/channel/msgid
  "channel": "string",               // @MalikaBozor
  "posted_at": "timestamp",          // ISO 8601 format
  
  "extra_attributes": {}             // For unknown fields
}

Index settings:
- filterableAttributes: ["category", "subcategory", "price", "data.*", "channel"]
- searchableAttributes: ["item", "searchable_text", "data", "category"]
- sortableAttributes: ["price", "posted_at"]
- typoTolerance: enabled (maxTypos: 2)
- ranking rules: ["words", "typo", "proximity", "attribute", "sort", "exactness"]

================================================================================
8. IMPLEMENTATION ROADMAP
================================================================================

STATUS LEGEND:
[ ] Not Started
[~] In Progress  
[✓] Completed

PHASE 1: PROJECT SETUP
├─ [✓] Architecture finalized
├─ [✓] Tech stack decided
├─ [✓] Create project structure
│   ├─ [✓] Initialize Git repository
│   ├─ [✓] Create directory structure
│   ├─ [✓] Setup .env template
│   └─ [✓] Create requirements.txt
├─ [ ] Docker setup
│   ├─ [ ] Create docker-compose.yml (Meilisearch + PostgreSQL)
│   ├─ [ ] Test Meilisearch connection
│   └─ [ ] Test PostgreSQL connection
└─ [ ] Configuration management
    ├─ [ ] Create src/config.py
    └─ [ ] Environment validation

PHASE 2: DATABASE LAYER
├─ [ ] PostgreSQL setup
│   ├─ [ ] Create database migrations
│   ├─ [ ] Implement schema (4 tables)
│   └─ [ ] Create database models (SQLAlchemy)
├─ [ ] Meilisearch setup
│   ├─ [ ] Initialize index
│   ├─ [ ] Configure filterable/searchable attributes
│   └─ [ ] Test basic indexing/searching
└─ [ ] Database utilities
    ├─ [ ] Connection pooling
    └─ [ ] Error handling

PHASE 3: AI PIPELINE
├─ [ ] Create category schemas (src/schemas.py)
│   ├─ [ ] Define electronics subcategories
│   ├─ [ ] Define real_estate subcategories
│   ├─ [ ] Define vehicles subcategories
│   └─ [ ] Define jobs subcategories
├─ [ ] Router AI (src/ai_parser.py)
│   ├─ [ ] Write router prompt template
│   ├─ [ ] Implement classification function
│   ├─ [ ] Add confidence threshold handling
│   └─ [ ] Test with sample messages
├─ [ ] Specialist AI (src/ai_parser.py)
│   ├─ [ ] Write specialist prompt templates (per category)
│   ├─ [ ] Implement extraction function
│   ├─ [ ] Add field normalization
│   └─ [ ] Test extraction accuracy
└─ [ ] Query Parser AI (src/ai_parser.py)
    ├─ [ ] Write query parsing prompt
    ├─ [ ] Implement filter extraction
    ├─ [ ] Handle Uzbek comparison phrases
    └─ [ ] Test with sample queries

PHASE 4: CRAWLER
├─ [ ] Telethon setup (src/crawler.py)
│   ├─ [ ] Session management (multi-account)
│   ├─ [ ] Channel joining logic
│   └─ [ ] Event handler for new messages
├─ [ ] Message processing
│   ├─ [ ] Text extraction
│   ├─ [ ] Media download (images)
│   ├─ [ ] Metadata extraction (timestamp, link)
│   └─ [ ] Duplicate detection
├─ [ ] Integration with AI pipeline
│   ├─ [ ] Send message to Router AI
│   ├─ [ ] Send to Specialist AI
│   └─ [ ] Error handling (retry logic)
└─ [ ] Indexing integration
    ├─ [ ] Build Meilisearch document
    ├─ [ ] Index to Meilisearch
    └─ [ ] Update PostgreSQL tracking

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
