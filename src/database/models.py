"""SQLAlchemy database models."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(100), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    api_id = Column(Integer, nullable=False)
    api_hash = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    channels = relationship("MonitoredChannel", back_populates="session")


class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_message_id = Column(BigInteger, default=0, nullable=False)
    total_indexed = Column(Integer, default=0, nullable=False)
    session_id = Column(Integer, ForeignKey("telegram_sessions.id"), nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    last_scraped_at = Column(DateTime, nullable=True)

    session = relationship("TelegramSession", back_populates="channels")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_channel = Column(Text, nullable=False, index=True)
    source_message_id = Column(BigInteger, nullable=False)
    raw_text = Column(Text, nullable=False)
    has_media = Column(Boolean, default=False, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    item_metadata = Column("metadata", JSONB, nullable=True)
    price = Column(Float, nullable=True, index=True)
    currency = Column(String(10), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    indexed_at = Column(DateTime, nullable=False, default=func.now())


class SearchAnalytics(Base):
    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    results_count = Column(Integer, nullable=True)
    searched_at = Column(DateTime, default=func.now(), nullable=False)
    response_time_ms = Column(Integer, nullable=True)
