# Copilot Instructions — Tele-Google

## Engineering Principles

Every change to this codebase must follow these principles. Not as suggestions — as requirements.

### Single Responsibility
Each module, class, and function does one thing. If you're adding logic to a function that already has a clear purpose, that logic probably belongs elsewhere. A 400-line function is a design failure.

### Don't Repeat Yourself
Before writing any utility, helper, or pattern — **search the codebase** for existing implementations. This project has a history of duplicated code (e.g., 3 HTML escape functions across 3 files). If it exists, use it. If it's broken, fix it — don't create a parallel version.

### Separation of Concerns
- **Database** logic stays in `src/database/repository.py` — nowhere else opens sessions or writes queries
- **AI/prompt** logic stays in `src/ai_parser.py` and `src/prompts.py`
- **Presentation** (message formatting, escaping) stays in `src/bot_utils/formatters.py`
- **Business logic** (search pipeline, deal detection) stays in `src/search_engine.py` and `src/crawler.py`
- **Configuration** stays in `src/config.py` and `.env`

If your change crosses these boundaries, you're likely violating SoC.

### Open/Closed
Extend behavior through new methods or parameters. Don't modify working internals of existing methods to accommodate a new feature. If `search()` works, don't gut it — add a new method or compose on top.

### Dependency Inversion
Depend on abstractions (the singleton getters), not on concrete instances. Don't instantiate services directly — use `get_config()`, `get_ai_parser()`, `get_search_engine()`, etc.

### No Dead Code
Every column in the schema must be read somewhere. Every function must be called. Every import must be used. If it's not needed yet, it doesn't exist yet. Remove before adding.

### Minimal Surface Area
- Don't add new files when extending an existing one works
- Don't add new dependencies without explicit approval
- Don't add columns/fields "for the future" — add them when they're needed
- If a 5-line change solves the problem, don't write 50 lines

---

## Architecture

Two processes sharing PostgreSQL+pgvector:
- **Crawler** (`run_crawler.py`): Telethon → AI classify → embed → store
- **Bot** (`run_bot.py`): Aiogram 3.x → embed query → pgvector top 50 → AI rerank → top 5

Pipeline: `message → classify_and_extract (GPT-4o-mini) → embed (text-embedding-3-small, 1536d) → Listing row`

Each process owns its own `Notifier` singleton instance. They share nothing at runtime except the database.

## Known Traps (MUST READ)

### `item_metadata` vs `metadata`
SQLAlchemy's `Base` reserves `metadata`. Our model maps:
```python
item_metadata = Column("metadata", JSONB)  # DB column is "metadata"
```
**Always `listing.item_metadata` in Python.** `listing.metadata` silently returns SQLAlchemy internals.

### Alembic Migrations
Alembic is the **sole schema manager**. `connection.py` no longer calls `create_all()`.
- Models live in `src/database/models.py` (source of truth)
- To generate a migration: `alembic revision --autogenerate -m "description"`
- To apply: `alembic upgrade head`
- To check status: `alembic current` / `alembic history`
- `env.py` handles async engine + pgvector `Vector` type rendering
- The baseline migration (`0001_baseline`) represents the schema as of 2026-02-16

### HTML Escaping
One canonical function: `_esc_html()` in `src/bot_utils/formatters.py`. Other escape functions exist in notifier.py and admin.py (the one in admin.py is buggy — misses `&`). Use `_esc_html()`. Don't create new ones.

### PostgreSQL Port
Port **5433**, not 5432. See `docker-compose.yml`.

### Memory
EC2 t3.micro, 914 MiB RAM + 2GB swap. No bulk queries without LIMIT. No large in-memory collections.

## Patterns to Follow

| Pattern | How | Where |
|---------|-----|-------|
| DB access | Static async methods in Repository classes | `src/database/repository.py` |
| Session management | `async with get_session() as session:` inside repository methods only | `src/database/connection.py` |
| Schema changes | Alembic autogenerate + review + apply | `migrations/versions/` |
| Service access | Lazy singletons via `get_X()` functions | Each service module |
| Config | Pydantic Settings from `.env`, prefixed (`TELEGRAM_`, `OPENAI_`, `DB_`, `BOT_`) | `src/config.py` |
| Error handling | `logger.error(f"<context> failed: {e}")`, recover and continue, never crash | Everywhere |
| AI prompts | System + user prompt templates | `src/prompts.py` only |
| Text formatting | HTML escaping, result formatting | `src/bot_utils/formatters.py` only |

## Module Map

| Module | Responsibility | Boundary |
|--------|---------------|----------|
| `src/database/` | Schema, connections, all data access | Only place that touches the DB |
| `src/ai_parser.py` + `src/prompts.py` | AI classification, extraction, reranking | Only place that calls OpenAI chat completions |
| `src/embeddings.py` | Vector generation | Only place that calls OpenAI embeddings |
| `src/crawler.py` | Ingestion pipeline | Orchestrates AI + embeddings + repository for new messages |
| `src/search_engine.py` | Search, deal detection, valuation | Orchestrates embeddings + AI + repository for queries |
| `src/bot.py` | User-facing Telegram interface | Thin — delegates to search_engine, formatters, i18n |
| `src/bot_utils/admin.py` | Admin-only commands | Operational tooling, not user features |
| `src/notifier.py` | Log channel events | Fire-and-forget, never blocks caller |
| `src/config.py` | Configuration | Pure data, no logic |
| `src/i18n.py` | Translations | uz/ru/en in `src/locales/*.json` |

## Running Locally
```bash
docker-compose up -d            # PostgreSQL+pgvector on port 5433
pip install -r requirements.txt
cp .env.template .env           # Fill credentials
python run_crawler.py           # Terminal 1
python run_bot.py               # Terminal 2
```
