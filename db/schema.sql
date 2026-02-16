-- =============================================================================
-- Tele-Google Database Schema
-- =============================================================================
-- PostgreSQL 15.x + pgvector
-- Database: tele_google
-- Port: 5433 (mapped from container 5432)
--
-- This file is the canonical schema reference. It is generated from production
-- via `pg_dump --schema-only` and kept in sync with src/database/models.py.
--
-- To recreate from scratch:
--   docker exec -i tele-google-postgres psql -U postgres -d tele_google < db/schema.sql
--
-- NOTE: connection.py calls Base.metadata.create_all() on startup, which will
-- create any missing tables automatically from models.py. This file serves as
-- documentation and a reproducible baseline.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

-- Telethon session storage (currently unused, 0 rows)
CREATE TABLE IF NOT EXISTS public.telegram_sessions (
    id          serial          PRIMARY KEY,
    session_name    varchar(100)    NOT NULL,
    phone_number    varchar(20)     NOT NULL,
    api_id          integer         NOT NULL,
    api_hash        varchar(100)    NOT NULL,
    is_active       boolean         NOT NULL,
    last_used_at    timestamp,
    created_at      timestamp       NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_telegram_sessions_session_name
    ON public.telegram_sessions (session_name);


-- Channels being monitored by the crawler
CREATE TABLE IF NOT EXISTS public.monitored_channels (
    id              serial          PRIMARY KEY,
    username        varchar(100)    NOT NULL,
    title           varchar(255),
    is_active       boolean         NOT NULL,
    last_message_id bigint          NOT NULL,
    total_indexed   integer         NOT NULL,
    session_id      integer         REFERENCES public.telegram_sessions(id),
    added_at        timestamp       NOT NULL,
    last_scraped_at timestamp
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_monitored_channels_username
    ON public.monitored_channels (username);


-- Core table: marketplace listings extracted from Telegram messages
CREATE TABLE IF NOT EXISTS public.listings (
    id                          bigserial       PRIMARY KEY,
    source_channel              text            NOT NULL,
    source_message_id           bigint          NOT NULL,
    raw_text                    text            NOT NULL,
    has_media                   boolean         NOT NULL,
    embedding                   vector(1536)    NOT NULL,
    created_at                  timestamp       NOT NULL,
    indexed_at                  timestamp       NOT NULL,
    metadata                    jsonb,                      -- Python attr: item_metadata
    price                       double precision,
    currency                    varchar(10),
    message_link                text,
    classification_confidence   double precision,
    processing_time_ms          integer,
    raw_ai_response             text,
    deal_score                  double precision,

    CONSTRAINT uq_listing_channel_message UNIQUE (source_channel, source_message_id)
);

CREATE INDEX IF NOT EXISTS ix_listings_source_channel ON public.listings (source_channel);
CREATE INDEX IF NOT EXISTS ix_listings_created_at     ON public.listings (created_at);
CREATE INDEX IF NOT EXISTS ix_listings_price          ON public.listings (price);
CREATE INDEX IF NOT EXISTS ix_listings_currency       ON public.listings (currency);
CREATE INDEX IF NOT EXISTS ix_listings_metadata       ON public.listings USING gin (metadata);


-- Bot users (tracked on first interaction)
CREATE TABLE IF NOT EXISTS public.users (
    telegram_id         bigint          PRIMARY KEY,
    username            varchar(100),
    first_name          varchar(100),
    last_name           varchar(100),
    language_code       varchar(10),
    preferred_language  varchar(10),
    first_seen_at       timestamp       DEFAULT now(),
    last_active_at      timestamp       DEFAULT now(),
    total_searches      integer         DEFAULT 0
);


-- Search analytics for usage tracking
CREATE TABLE IF NOT EXISTS public.search_analytics (
    id                  serial          PRIMARY KEY,
    user_id             bigint          NOT NULL,
    query_text          text            NOT NULL,
    results_count       integer,
    searched_at         timestamp       NOT NULL,
    response_time_ms    integer,
    result_listing_ids  jsonb,
    clicked_listing_id  bigint
);

CREATE INDEX IF NOT EXISTS ix_search_analytics_user_id
    ON public.search_analytics (user_id);
