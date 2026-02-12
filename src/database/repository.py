"""
Database Repository Layer
Provides clean interface for database operations, eliminating query duplication
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert

from src.database.connection import get_session
from src.database.models import MonitoredChannel, TelegramSession, Listing


class ChannelRepository:
    """Repository for MonitoredChannel operations"""
    
    @staticmethod
    async def get_all_active() -> List[MonitoredChannel]:
        """Get all active channels"""
        async with get_session() as session:
            result = await session.execute(
                select(MonitoredChannel).where(MonitoredChannel.is_active == True)
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_by_username(username: str) -> Optional[MonitoredChannel]:
        """Get channel by username"""
        async with get_session() as session:
            result = await session.execute(
                select(MonitoredChannel).where(MonitoredChannel.username == username)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def create(username: str, title: Optional[str] = None, session_id: Optional[int] = None) -> MonitoredChannel:
        """Create new monitored channel"""
        async with get_session() as session:
            channel = MonitoredChannel(
                username=username,
                title=title or username,
                is_active=True,
                session_id=session_id
            )
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            return channel
    
    @staticmethod
    async def deactivate(username: str) -> bool:
        """Deactivate channel by username"""
        async with get_session() as session:
            result = await session.execute(
                update(MonitoredChannel)
                .where(MonitoredChannel.username == username)
                .values(is_active=False)
            )
            await session.commit()
            return bool(result.rowcount) if hasattr(result, 'rowcount') else True  # type: ignore[attr-defined]
    
    @staticmethod
    async def update_stats(username: str, message_id: int) -> None:
        """Update channel statistics"""
        async with get_session() as session:
            await session.execute(
                insert(MonitoredChannel)
                .values(
                    username=username,
                    total_indexed=1,
                    last_message_id=message_id,
                    last_scraped_at=datetime.utcnow()
                )
                .on_conflict_do_update(
                    index_elements=['username'],
                    set_=dict(
                        total_indexed=MonitoredChannel.total_indexed + 1,
                        last_message_id=message_id,
                        last_scraped_at=datetime.utcnow()
                    )
                )
            )
            await session.commit()


class SessionRepository:
    """Repository for TelegramSession operations"""
    
    @staticmethod
    async def get_all_active() -> List[TelegramSession]:
        """Get all active Telegram sessions"""
        async with get_session() as session:
            result = await session.execute(
                select(TelegramSession).where(TelegramSession.is_active == True)
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_by_phone(phone: str) -> Optional[TelegramSession]:
        """Get session by phone number"""
        async with get_session() as session:
            result = await session.execute(
                select(TelegramSession).where(TelegramSession.phone_number == phone)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def create(phone: str, session_name: str, api_id: int, api_hash: str) -> TelegramSession:
        """Create new Telegram session"""
        async with get_session() as session:
            telegram_session = TelegramSession(
                phone_number=phone,
                session_name=session_name,
                api_id=api_id,
                api_hash=api_hash,
                is_active=True
            )
            session.add(telegram_session)
            await session.commit()
            await session.refresh(telegram_session)
            return telegram_session
    
    @staticmethod
    async def deactivate(phone: str) -> bool:
        """Deactivate session by phone number"""
        async with get_session() as session:
            result = await session.execute(
                update(TelegramSession)
                .where(TelegramSession.phone_number == phone)
                .values(is_active=False)
            )
            await session.commit()
            return bool(result.rowcount) if hasattr(result, 'rowcount') else True  # type: ignore[attr-defined]


class ListingRepository:
    """Repository for Listing operations"""
    
    @staticmethod
    async def exists(channel: str, message_id: int) -> bool:
        """Check if listing already exists"""
        async with get_session() as session:
            result = await session.execute(
                select(Listing).where(
                    Listing.source_channel == channel,
                    Listing.source_message_id == message_id
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
        created_at: Optional[datetime] = None
    ) -> Listing:
        """Create new listing"""
        async with get_session() as session:
            listing = Listing(
                source_channel=source_channel,
                source_message_id=source_message_id,
                raw_text=raw_text,
                has_media=has_media,
                embedding=embedding,
                created_at=created_at or datetime.utcnow()
            )
            session.add(listing)
            await session.commit()
            await session.refresh(listing)
            return listing
