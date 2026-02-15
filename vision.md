# Tele-Google — Vision & Architecture

## What Is This?

A marketplace intelligence platform for Uzbekistan's Telegram economy. Telegram is where
the informal marketplace lives — phones, cars, apartments, jobs, electronics — spread across
dozens of fragmented channels. There is no unified search, no price comparison, no deal detection.

Tele-Google fills that gap.

## Four Pillars

### 1. Search (Core Product)
Users describe what they want in natural language (Uzbek/Russian/English). We return the
exact right listings ranked by relevance. **If search doesn't nail user intent, nothing else
matters.** This is the primary interface and the hook that brings users in.

Pipeline: User query → embed (text-embedding-3-small) → pgvector top 50 → AI rerank (GPT-4o-mini) → top 5 results.

### 2. Valuation (Utility)
"How much is my iPhone 13 128GB worth?" — answered from aggregated pricing data. Like Kelley
Blue Book for Uzbekistan's Telegram marketplace. Once we have enough listings per
category/brand/model/condition, we compute fair market value. Users get value, we get
engagement and trust.

### 3. Hot Deals (Revenue Engine)
Detect listings priced significantly below market (using the valuation engine). Two tiers:
- **Free**: Public Telegram channel publishes hot deals with 3–4 hour delay.
- **Premium**: Instant alerts. Subscribers pay to see deals first. Speed = money.

This is the monetization model.

### 4. Data Aggregation (Strategic Asset)
Every listing, price, metadata field, search query, user interaction — structured properly,
this data powers valuation and deal detection, enables trend analysis, and has standalone
commercial value. **Metadata extraction quality is critical** — every field is a future
training sample for custom pricing/evaluation models.

## How Pillars Connect

```
Telegram Channels
       │
       ▼
  Crawler (Telethon) ─── real-time subscription + backfill
       │
       ▼
  AI Pipeline ─── classify → extract metadata → embed → store
       │
       ▼
  PostgreSQL + pgvector ─── structured listings with vectors
       │
       ├──── Search Bot (Aiogram) ← user queries
       │         └── AI rerank → results
       │
       ├──── Valuation Engine ← enough data per category
       │         └── median/percentile pricing
       │
       ├──── Deal Detection ← compare to valuation
       │         ├── Free channel (delayed)
       │         └── Premium alerts (instant) ← revenue
       │
       └──── Data Asset ← analytics, ML training, business intelligence
```

## Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Crawler         | Telethon (user client)              |
| Bot             | Aiogram 3.x                        |
| AI              | OpenAI GPT-4o-mini + embeddings     |
| Database        | PostgreSQL + pgvector               |
| Hosting         | AWS EC2 t3.micro (Ubuntu 24.04)     |
| Language        | Python 3.12+                        |
| Process mgmt    | systemd                             |

## Users

- **Buyers**: Regular people in Uzbekistan searching for items. Speak Uzbek and Russian.
  Want fast, relevant results with fair pricing context.
- **Admin**: Full remote control from Telegram — channels, deployment, auth, health, SQL.
  Zero SSH goal.
- **Premium subscribers** (future): Pay for instant deal alerts.

## Key Principle

**Data quality above all.** Every extracted field is a future training sample. Inconsistent
metadata = garbage training data = useless pricing models. Classification confidence,
field naming, validation, and prompt engineering must be rigorous.

## Infrastructure

- EC2: ubuntu@13.60.84.34, SSH key: ~/.ssh/questpath-aws-key.pem
- PostgreSQL: Docker container `tele-google-postgres` on port 5433
- Systemd services: `tele-google-bot`, `tele-google-crawler`
- Telegram Bot: @tele_google_bot (token: 8508588510:AAEhQ...)
- Crawler account: API_ID=38368503, phone=+998333931751
- Admin user IDs: [1415751701, 8046347985]
- Log channel: -1003736972178
