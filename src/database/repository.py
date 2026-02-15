"""Repository layer — clean interface for all DB operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from src.database.connection import get_session
from src.database.models import MonitoredChannel, TelegramSession, Listing, User


class ChannelRepository:
    @staticmethod
    async def get_all_active() -> List[MonitoredChannel]:
        async with get_session() as session:
            result = await session.execute(
                select(MonitoredChannel).where(MonitoredChannel.is_active == True)
            )
            return list(result.scalars().all())

    @staticmethod
    async def deactivate(username: str) -> bool:
        async with get_session() as session:
            result = await session.execute(
                update(MonitoredChannel)
                .where(MonitoredChannel.username == username)
                .values(is_active=False)
            )
            await session.commit()
            return bool(result.rowcount)

    @staticmethod
    async def update_stats(username: str, message_id: int) -> None:
        """Upsert channel stats (insert on first encounter, increment otherwise)."""
        async with get_session() as session:
            await session.execute(
                insert(MonitoredChannel)
                .values(
                    username=username,
                    total_indexed=1,
                    last_message_id=message_id,
                    last_scraped_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["username"],
                    set_=dict(
                        total_indexed=MonitoredChannel.total_indexed + 1,
                        last_message_id=message_id,
                        last_scraped_at=datetime.utcnow(),
                    ),
                )
            )
            await session.commit()


class SessionRepository:
    @staticmethod
    async def get_all_active() -> List[TelegramSession]:
        async with get_session() as session:
            result = await session.execute(
                select(TelegramSession).where(TelegramSession.is_active == True)
            )
            return list(result.scalars().all())


class ListingRepository:
    @staticmethod
    async def exists(channel: str, message_id: int) -> bool:
        async with get_session() as session:
            result = await session.execute(
                select(Listing.id).where(
                    Listing.source_channel == channel,
                    Listing.source_message_id == message_id,
                )
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def create(
        source_channel: str,
        source_message_id: int,
        raw_text: str,
        has_media: bool,
        embedding: List[float],
        created_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
        message_link: Optional[str] = None,
        classification_confidence: Optional[float] = None,
        processing_time_ms: Optional[int] = None,
        raw_ai_response: Optional[str] = None,
    ) -> Listing:
        price = None
        currency = None
        if metadata:
            p = metadata.get("price")
            price = float(p) if p is not None else None
            currency = metadata.get("currency")
        async with get_session() as session:
            listing = Listing(
                source_channel=source_channel,
                source_message_id=source_message_id,
                raw_text=raw_text,
                has_media=has_media,
                embedding=embedding,
                created_at=created_at or datetime.utcnow(),
                item_metadata=metadata,
                price=price,
                currency=currency,
                message_link=message_link,
                classification_confidence=classification_confidence,
                processing_time_ms=processing_time_ms,
                raw_ai_response=raw_ai_response,
            )
            session.add(listing)
            await session.commit()
            await session.refresh(listing)
            return listing

    @staticmethod
    async def update_deal_score(listing_id: int, deal_score: float) -> None:
        async with get_session() as session:
            await session.execute(
                update(Listing)
                .where(Listing.id == listing_id)
                .values(deal_score=deal_score)
            )
            await session.commit()


class UserRepository:
    """Manage bot users for analytics and preference persistence."""

    @staticmethod
    async def upsert_from_message(
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> None:
        """Create or update user on every interaction."""
        async with get_session() as session:
            await session.execute(
                insert(User)
                .values(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    first_seen_at=datetime.utcnow(),
                    last_active_at=datetime.utcnow(),
                    total_searches=0,
                )
                .on_conflict_do_update(
                    index_elements=["telegram_id"],
                    set_=dict(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        language_code=language_code,
                        last_active_at=datetime.utcnow(),
                    ),
                )
            )
            await session.commit()

    @staticmethod
    async def increment_searches(telegram_id: int) -> None:
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    total_searches=User.total_searches + 1,
                    last_active_at=datetime.utcnow(),
                )
            )
            await session.commit()

    @staticmethod
    async def get_preferred_language(telegram_id: int) -> Optional[str]:
        async with get_session() as session:
            result = await session.execute(
                select(User.preferred_language).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def set_preferred_language(telegram_id: int, lang: str) -> None:
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(preferred_language=lang, last_active_at=datetime.utcnow())
            )
            await session.commit()
