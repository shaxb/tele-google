# Development Log — Tele-Google

This file tracks implementation progress, decisions, and technical debt. It serves as
persistent context across development sessions.

---

## Session: 2026-02-16 — Valuation, Formatting, Resilience

### Completed

1. **Crawler auth crash loop fix** — When session is invalid under systemd (no TTY),
   crawler now detects headless mode, logs CRITICAL, and sleeps 5min instead of crash-looping
   with SendCodeRequest floods that trigger Telegram rate limits.

2. **Search result formatting overhaul** — Results now show:
   - Extracted title (from metadata) instead of raw text blob
   - Price with proper currency formatting ($, сўм)
   - Category with emoji icons (🚗 car, 📱 phone, 🏠 apartment, etc.)
   - Condition (✨ new / ♻️ used)
   - Extra metadata highlights (brand, model, year, storage_gb, etc.)
   - Clean "View in @channel" link

3. **`/price` command (Pillar 2: Valuation)** — Users send `/price iPhone 13 128GB`
   and get market price estimates:
   - Embeds query → pgvector neighbors → filters priced listings → statistics
   - Returns: median (fair value), mean, min-max range, spread %, comparable listings
   - Minimum 3 samples required, similarity threshold 0.80
   - `SearchEngine.valuate()` method added

4. **Crawler resilience hardening**:
   - `IntegrityError` from unique constraint race conditions now handled gracefully
   - Message handler wrapped in try/except to prevent crash on single message
   - `import sys; sys.stdin.isatty()` check before Telethon interactive auth

5. **Deploy command fix** — `/deploy` was using `git pull origin main` but repo uses
   `master` branch. Fixed.

6. **Session re-authentication** — Local session expired, re-authenticated as Topdim_HQ
   with phone +998333931751, copied to EC2.

### Production State
- Bot: active (running), /price command live
- Crawler: active, monitoring 8 channels, authenticated as Topdim_HQ
- Both services on EC2 t3.micro with systemd

---

## Session: 2026-02-15 — Foundation + Pipeline Quality

### Status Before This Session

Working MVP with:
- Crawler monitoring 7 channels via Telethon (new SIM: +998333931751)
- Bot serving search queries with AI reranking
- GPT-4o-mini classify_and_extract() doing one-call classification + metadata extraction
- PostgreSQL + pgvector for storage and vector search
- Notifier system sending structured events to log channel
- Admin commands: /stats, /recent, /inspect, /health, /logs, /sql
- Running on EC2 t3.micro with 2GB swap

### Known Bugs (to fix this session)

1. **OpenAI sync client blocks event loop** — `ai_parser.py` uses sync `OpenAI()` client
   inside async crawler. Must switch to `AsyncOpenAI`.
2. **Hot-reload closure bug** — `_reload_channels()` in crawler.py has a lambda that
   captures loop variable `username` by reference. All handlers end up using the last
   username. Fix: capture as default parameter.
3. **No unique constraint on listings** — `(source_channel, source_message_id)` uniqueness
   is only app-level via `ListingRepository.exists()`. Add DB constraint.
4. **Deal detection never called** — `evaluate_deal()` exists but is never wired in.
5. **Backfill overcounts** — increments `indexed` for every message with text, not just
   those that pass classification.
6. **Language prefs in-memory** — `_prefs: Dict[int, str] = {}` in language.py, lost on
   restart.

### Implementation Plan (this session)

#### Phase 1: Bug Fixes
- [ ] Switch ai_parser.py to AsyncOpenAI
- [ ] Fix closure bug in crawler.py _reload_channels
- [ ] Add unique constraint on listings (source_channel, source_message_id)
- [ ] Fix backfill count logic

#### Phase 2: Users & Analytics
- [ ] Create `users` table (telegram_id PK, username, first_name, last_name,
      language_code, preferred_language, first_seen_at, last_active_at, total_searches)
- [ ] Create UserRepository with upsert_from_message()
- [ ] Replace in-memory language dict with DB
- [ ] Enrich search_analytics: add result_listing_ids (JSONB), clicked_listing_id
- [ ] Track user on every bot interaction

#### Phase 3: Pipeline Traceability
- [ ] Add to listings: message_link, classification_confidence, processing_time_ms,
      raw_ai_response
- [ ] Update classify_and_extract() to return confidence + timing + raw response
- [ ] Update prompt to include confidence field
- [ ] Update notifier to log full metadata breakdown

#### Phase 4: Admin Control
- [ ] /auth command — remote Telegram auth via bot
- [ ] /deploy command — git pull + restart from Telegram
- [ ] /restart bot|crawler — service restart command

#### Phase 5: Deal Detection Pipeline
- [ ] Wire evaluate_deal() into crawler after listing creation
- [ ] Call notifier.deal() when deal detected
- [ ] Store deal_score on listing

#### Phase 6: Deploy
- [ ] Apply DB migrations (ALTER TABLE)
- [ ] Git commit + push
- [ ] Deploy to EC2
- [ ] Verify all features

---

## File Map (key files and their responsibilities)

| File | Purpose | Lines |
|------|---------|-------|
| src/config.py | Pydantic settings from .env | ~80 |
| src/crawler.py | Telethon channel monitoring + message pipeline | ~300 |
| src/bot.py | Aiogram bot + search handler + periodic tasks | ~285 |
| src/ai_parser.py | OpenAI classify_and_extract + rerank | ~120 |
| src/prompts.py | AI prompt templates | ~80 |
| src/embeddings.py | text-embedding-3-small wrapper | ~40 |
| src/search_engine.py | pgvector search + evaluate_deal | ~150 |
| src/notifier.py | Telegram log channel notifications | ~220 |
| src/i18n.py | Translation loader | ~30 |
| src/database/models.py | SQLAlchemy ORM models | ~80 |
| src/database/connection.py | Async engine + session factory | ~50 |
| src/database/repository.py | Data access layer | ~150 |
| src/bot_utils/admin.py | Admin commands (/stats, /logs, /sql, etc.) | ~570 |
| src/bot_utils/formatters.py | Result formatting for bot | ~120 |
| src/bot_utils/language.py | Per-user language preferences | ~30 |
| src/utils/channels.py | channels.txt read/write | ~40 |
| src/utils/logger.py | Loguru config | ~20 |

## Database Schema

### listings
- id (BigInteger PK)
- source_channel (Text, indexed)
- source_message_id (BigInteger)
- raw_text (Text)
- has_media (Boolean)
- embedding (Vector(1536))
- item_metadata (Column("metadata", JSONB)) — NOTE: Python attr is item_metadata, DB col is metadata
- price (Float, indexed)
- currency (String(10))
- created_at (DateTime, indexed)
- indexed_at (DateTime)

### search_analytics
- id (Integer PK)
- user_id (BigInteger, indexed)
- query_text (Text)
- results_count (Integer)
- searched_at (DateTime)
- response_time_ms (Integer)

### telegram_sessions
- id (Integer PK), session_name, phone_number, api_id, api_hash, is_active, last_used_at, created_at

### monitored_channels
- id (Integer PK), username, title, is_active, last_message_id, total_indexed, session_id, added_at, last_scraped_at

## Critical Implementation Notes

- SQLAlchemy `metadata` is reserved in Declarative API. Our column is named `metadata` in DB
  but the Python attribute MUST be `item_metadata`. Access as `listing.item_metadata`.
- Alembic is broken. All schema changes done via direct `ALTER TABLE` through docker exec psql.
- The bot and crawler are separate processes. Each gets its own Notifier singleton.
- Session file is `data/sessions/default_session.session` (SQLite). Must be deleted to
  re-authenticate with a new phone number.
- EC2 has 914 MiB RAM + 2GB swap. Memory-conscious code required.
