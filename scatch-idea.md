================================================================================
PROJECT: TELE-GOOGLE (Telegram Search Engine)
================================================================================

1. PROJECT OVERVIEW
-------------------
A real-time search engine that indexes public Telegram channels (e.g., marketplaces) 
and makes them searchable via a Telegram Bot. It uses AI to parse unstructured 
messages into structured data (JSON) and a specialized search engine for typo-tolerant 
retrieval.

2. CORE LOGIC FLOW
------------------
[SOURCE: Telegram Channels] 
       ⬇ (Telethon Userbot)
[RAW TEXT] "iPhone 15 pro srochna 800$..."
       ⬇ (OpenAI GPT-4o-mini)
[STRUCTURED JSON] {"item": "iPhone 15 Pro", "price": 800, "currency": "USD"}
       ⬇ (Meilisearch)
[INDEX] Searchable Database
       ⬇ (Aiogram Bot)
[USER QUERY] "iPhone 15 cheap" -> [RESULTS] Link to original message

3. TECH STACK
-------------
A. DATA INGESTION (The "Ear")
   - Language: Python 3.10+
   - Library: Telethon (Acts as a real user to join/listen to channels)
   - Proxy: Optional (Residential proxy recommended if scaling >5 channels)

B. INTELLIGENCE (The "Brain")
   - Model: OpenAI GPT-4o-mini (Cost-effective, high speed, Uzbek-slang capable)
   - Role: Extract price, item name, and condition from messy text.

C. SEARCH ENGINE (The "Memory")
   - Engine: Meilisearch (Running in Docker)
   - Role: Stores JSON, handles typo-tolerance ("Ayfon" -> "iPhone"), sorting, and filtering.

D. INTERFACE (The "Face")
   - Library: Aiogram 3.x (Asynchronous Telegram Bot framework)
   - Role: Handles user queries and Inline Mode searching.

E. INFRASTRUCTURE
   - Database: SQLite (Simple tracking of "last_scraped_id" to prevent duplicates)
   - Containerization: Docker (For Meilisearch)

4. FILE STRUCTURE
-----------------
tele-google/
├── .env                    # Secrets (API_ID, BOT_TOKEN, OPENAI_KEY)
├── docker-compose.yml      # Config to run Meilisearch
├── requirements.txt        # Python dependencies
├── src/
│   ├── config.py           # Configuration loader
│   ├── crawler.py          # Telethon script (Listener)
│   ├── parser.py           # OpenAI API wrapper
│   ├── search.py           # Meilisearch client wrapper
│   └── bot.py              # Aiogram bot entry point
└── data/                   # Meilisearch data persistence

5. IMPLEMENTATION PHASES
------------------------

PHASE 1: INFRASTRUCTURE
   - Action: create `docker-compose.yml`
   - Code:
     version: '3'
     services:
       meilisearch:
         image: getmeili/meilisearch:v1.6
         ports:
           - "7700:7700"
         environment:
           - MEILI_MASTER_KEY=masterKey
         volumes:
           - ./meili_data:/meili_data

PHASE 2: THE CRAWLER (crawler.py)
   - Use `Telethon` to log in as a User.
   - Listen to `events.NewMessage(chats=['@MalikaBozor'])`.
   - On new message: Print raw text to console.

PHASE 3: THE PARSER (parser.py)
   - Create a function `extract_data(text)`.
   - Call OpenAI API with a system prompt: 
     "Extract {item, price, currency, condition} from this Uzbek text to JSON."
   - Return clean Dictionary.

PHASE 4: INDEXING (search.py)
   - Initialize Meilisearch client.
   - Create index 'market'.
   - Update `crawler.py` to send parsed data to Meilisearch.

PHASE 5: THE BOT (bot.py)
   - Use `Aiogram`.
   - Command `/search <query>` -> Queries Meilisearch -> Returns formatted results with links.

6. KEY DEPENDENCIES (requirements.txt)
--------------------------------------
telethon
aiogram
openai
meilisearch
python-dotenv