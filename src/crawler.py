"""Telegram channel crawler — monitors channels and indexes listings.

Pipeline per message: text → duplicate check → is_listing? → embed → store.
Watches channels.txt for hot-reload every 30 s.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from sqlalchemy.exc import IntegrityError
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message as TelegramMessage

from src.ai_parser import get_ai_parser
from src.config import get_config
from src.database.connection import init_db
from src.database.repository import ChannelRepository, ListingRepository, SessionRepository
from src.embeddings import get_embedding_generator
from src.notifier import get_notifier
from src.search_engine import get_search_engine
from src.utils.channels import load_channels, get_file_mtime

SESSIONS_DIR = Path("data/sessions")


class TelegramCrawler:
    def __init__(self) -> None:
        self.config = get_config()
        self.clients: List[TelegramClient] = []
        self.active_channels: Set[str] = set()
        self._chat_id_to_username: Dict[int, str] = {}
        self.ai_parser = get_ai_parser()
        self.embedding_gen = get_embedding_generator()
        self._channels_mtime = 0.0
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    async def _auth_client(self, session_path: str, api_id: int, api_hash: str, phone: str) -> TelegramClient:
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            import sys
            if not sys.stdin.isatty():
                # Running under systemd / headless — cannot prompt for code
                await client.disconnect()
                raise RuntimeError(
                    f"Session '{session_path}' is not authorized and stdin is not a TTY. "
                    "Use /auth command from the bot, or run the crawler interactively to authenticate."
                )
            await client.start(phone=phone)  # type: ignore[misc]
        return client

    async def initialize_clients(self) -> None:
        db_sessions = await SessionRepository.get_all_active()

        if not db_sessions:
            logger.info("No DB sessions — using default from .env")
            client = await self._auth_client(
                str(SESSIONS_DIR / "default_session"),
                self.config.telegram.api_id,
                self.config.telegram.api_hash,
                self.config.telegram.phone,
            )
            self.clients.append(client)
        else:
            for s in db_sessions:
                client = await self._auth_client(
                    str(SESSIONS_DIR / s.session_name),
                    s.api_id, s.api_hash, s.phone_number,  # type: ignore[arg-type]
                )
                self.clients.append(client)

        logger.info(f"Active Telethon clients: {len(self.clients)}")

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------

    def _load_channels(self) -> List[str]:
        channels = load_channels()
        self._channels_mtime = get_file_mtime()
        return channels

    async def join_channels(self) -> None:
        if not self.clients:
            logger.error("No clients available")
            return

        channels = self._load_channels()
        for idx, username in enumerate(channels):
            client = self.clients[idx % len(self.clients)]
            try:
                entity = await client.get_entity(username)
                # Actually join/subscribe so we receive new messages
                try:
                    await client(JoinChannelRequest(entity))  # type: ignore[arg-type]
                except Exception:
                    pass  # Already joined or can't join — still try to monitor
                self.active_channels.add(username)
                if hasattr(entity, "id"):
                    self._chat_id_to_username[entity.id] = username  # type: ignore[union-attr]
                logger.success(f"Joined {username}")
            except Exception as e:
                logger.error(f"Failed to join {username}: {e}")

    async def _reload_channels(self) -> None:
        """Hot-reload channels.txt if it changed on disk."""
        current_mtime = get_file_mtime()
        if current_mtime <= self._channels_mtime:
            return

        logger.info("channels.txt changed — reloading")
        new = set(self._load_channels())
        added = new - self.active_channels
        removed = self.active_channels - new

        if removed:
            logger.info(f"Removed channels: {removed}")
            self.active_channels -= removed

        for username in added:
            client = self.clients[len(self.active_channels) % len(self.clients)]
            try:
                entity = await client.get_entity(username)
                try:
                    await client(JoinChannelRequest(entity))  # type: ignore[arg-type]
                except Exception:
                    pass

                @client.on(events.NewMessage(chats=[entity]))
                async def handler(event: events.NewMessage.Event, _u=username) -> None:
                    await self.process_message(event)

                self.active_channels.add(username)
                if hasattr(entity, "id"):
                    self._chat_id_to_username[entity.id] = username  # type: ignore[union-attr]
                logger.success(f"Added {username} (hot-reload)")
            except Exception as e:
                logger.error(f"Failed to add {username}: {e}")

    # ------------------------------------------------------------------
    # Message processing pipeline
    # ------------------------------------------------------------------

    async def _resolve_channel_id(self, event: events.NewMessage.Event) -> Optional[str]:
        chat = await event.get_chat()
        if not chat:
            return None
        # Prefer our own mapping (always stores @username from channels.txt)
        chat_id = getattr(chat, "id", None)
        if chat_id and chat_id in self._chat_id_to_username:
            return self._chat_id_to_username[chat_id]
        # Fallback for channels added dynamically
        if hasattr(chat, "username") and chat.username:
            u = chat.username
            return f"@{u}" if not u.startswith("@") else u
        return str(chat_id) if chat_id else None

    async def process_message(self, event: events.NewMessage.Event) -> None:
        """text → duplicate check → is_listing? → embed → store"""
        message: TelegramMessage = event.message
        channel_id = await self._resolve_channel_id(event)
        if not channel_id:
            return

        raw_text = (message.message or "").strip()
        if not raw_text:
            return

        notifier = get_notifier()
        notifier.count("messages_seen")

        if await ListingRepository.exists(channel_id, message.id):
            return

        try:
            result = await self.ai_parser.classify_and_extract(raw_text)
            if result is None:
                notifier.count("messages_skipped")
                return

            metadata = result["metadata"]
            confidence = result["confidence"]
            raw_ai_response = result["raw_response"]
            processing_time_ms = result["processing_time_ms"]

            embedding = await self.embedding_gen.generate(raw_text)
            if not embedding:
                return

            # Build message link
            channel_clean = channel_id.lstrip("@") if channel_id.startswith("@") else channel_id
            message_link = f"https://t.me/{channel_clean}/{message.id}"

            msg_date = message.date.replace(tzinfo=None) if message.date else datetime.utcnow()
            try:
                listing = await ListingRepository.create(
                    source_channel=channel_id,
                    source_message_id=message.id,
                    raw_text=raw_text,
                    has_media=bool(message.media),
                    embedding=embedding,
                    created_at=msg_date,
                    metadata=metadata,
                    message_link=message_link,
                    classification_confidence=confidence,
                    processing_time_ms=processing_time_ms,
                    raw_ai_response=raw_ai_response,
                )
            except IntegrityError:
                # Race condition: another process already indexed this message
                logger.debug(f"Duplicate message {message.id} from {channel_id} — skipping")
                return
            await ChannelRepository.update_stats(channel_id, message.id)

            title = metadata.get("title", "?")  # type: ignore[union-attr]
            price_info = f" | ${metadata.get('price', '?')}" if metadata.get("price") else ""
            logger.success(f"Indexed message {message.id} from {channel_id}{price_info} ({confidence:.0%} conf, {processing_time_ms}ms)")

            await notifier.listing(
                channel=channel_id,
                title=title,
                price=metadata.get("price"),  # type: ignore[union-attr]
                currency=metadata.get("currency"),  # type: ignore[union-attr]
                category=metadata.get("category"),  # type: ignore[union-attr]
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                message_link=message_link,
                metadata=metadata,
            )

            # Deal detection — if listing has price + currency, compare to market
            listing_price = metadata.get("price")  # type: ignore[union-attr]
            listing_currency = metadata.get("currency")  # type: ignore[union-attr]
            if listing_price and listing_currency and embedding:
                try:
                    deal = await get_search_engine().evaluate_deal(
                        embedding=embedding,
                        price=float(listing_price),
                        currency=listing_currency,
                    )
                    if deal:
                        await ListingRepository.update_deal_score(listing.id, deal["deviation"])  # type: ignore[arg-type]
                        if deal["is_deal"]:
                            await notifier.deal(
                                title=title,
                                price=float(listing_price),
                                currency=listing_currency,
                                median=deal["median_price"],
                                deviation=deal["deviation"],
                            )
                            logger.info(f"🔥 Deal detected: {title} — {abs(deal['deviation'])*100:.0f}% below median")
                except Exception as e:
                    logger.warning(f"Deal evaluation failed: {e}")

        except Exception as e:
            logger.error(f"Failed to process message {message.id}: {e}", exc_info=True)
            await notifier.error("process_message", e)

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    async def start_monitoring(self) -> None:
        if not self.clients:
            logger.error("No clients initialized")
            return

        for client in self.clients:
            @client.on(events.NewMessage(chats=list(self.active_channels)))
            async def handler(event: events.NewMessage.Event) -> None:
                try:
                    await self.process_message(event)
                except Exception as e:
                    logger.error(f"Unhandled error in message handler: {e}")

        logger.success(f"Monitoring {len(self.active_channels)} channels")

        async def file_watcher() -> None:
            while True:
                await asyncio.sleep(30)
                try:
                    await self._reload_channels()
                except Exception as e:
                    logger.error(f"Channel reload error: {e}")

        await asyncio.gather(
            *[client.run_until_disconnected() for client in self.clients],  # type: ignore[misc]
            file_watcher(),
            return_exceptions=True,
        )

    # ------------------------------------------------------------------
    # Backfill
    # ------------------------------------------------------------------

    async def backfill_channel(self, channel_username: str, limit: int = 100, min_id: int = 0) -> int:
        """Fetch historical messages from a channel and index them."""
        if not self.clients:
            return 0

        client = self.clients[0]
        indexed = 0
        logger.info(f"Backfilling {channel_username} (limit={limit}, min_id={min_id})")

        try:
            entity = await client.get_entity(channel_username)  # type: ignore[arg-type]

            class _FakeEvent:
                """Lightweight adapter so process_message can handle backfill messages."""
                def __init__(self, msg: TelegramMessage, chat: Any) -> None:
                    self.message = msg
                    self._chat = chat
                async def get_chat(self) -> Any:
                    return self._chat

            async for message in client.iter_messages(entity, limit=limit, min_id=min_id):  # type: ignore[arg-type]
                if message.message and message.message.strip():
                    try:
                        await self.process_message(_FakeEvent(message, entity))  # type: ignore[arg-type]
                        indexed += 1
                    except Exception as e:
                        logger.warning(f"Backfill skip message {message.id}: {e}")
                    await asyncio.sleep(0.5)

            logger.success(f"Backfill done: {indexed} messages indexed from {channel_username}")
        except Exception as e:
            logger.error(f"Backfill failed: {e}", exc_info=True)

        return indexed

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Full startup: DB → clients → channels → monitor."""
        notifier = get_notifier()
        try:
            logger.info("=" * 60)
            logger.info("TELEGRAM CRAWLER — Starting")
            logger.info("=" * 60)
            await init_db()
            await self.initialize_clients()
            await self.join_channels()
            await notifier.startup("Crawler")
            await notifier.start()
            await self.start_monitoring()
        except KeyboardInterrupt:
            await notifier.shutdown("Crawler")
            await notifier.stop()
            await self.stop()
        except RuntimeError as e:
            # Auth failure or similar — log clearly and exit without rapid restart
            logger.critical(f"Crawler startup failed (non-retryable): {e}")
            await notifier.error("startup", e)
            await notifier.stop()
            await self.stop()
            # Sleep so systemd doesn't restart us in a tight loop
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Crawler failed: {e}", exc_info=True)
            await notifier.shutdown("Crawler")
            await notifier.stop()
            await self.stop()

    async def stop(self) -> None:
        for client in self.clients:
            await client.disconnect()  # type: ignore[misc]
        logger.info("Crawler stopped")
