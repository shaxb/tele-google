"""
SQLAlchemy Database Models
Implements the exact schema from PROJECT_GUIDE.md Section 7
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TelegramSession(Base):
    """
    Manages multiple Telegram userbot sessions
    
    Each session represents a different Telegram account
    used for monitoring channels (multi-session support)
    """
    __tablename__ = "telegram_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(100), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    api_id = Column(Integer, nullable=False)
    api_hash = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship to monitored channels
    channels = relationship("MonitoredChannel", back_populates="session")
    
    def __repr__(self):
        return f"<TelegramSession(id={self.id}, session_name='{self.session_name}', phone='{self.phone_number}')>"


class MonitoredChannel(Base):
    """
    Tracks which Telegram channels are being monitored
    
    Stores channel metadata and indexing state for duplicate detection
    """
    __tablename__ = "monitored_channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)  # @MalikaBozor
    title = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_message_id = Column(BigInteger, default=0, nullable=False)  # For duplicate detection
    total_indexed = Column(Integer, default=0, nullable=False)
    session_id = Column(Integer, ForeignKey("telegram_sessions.id"), nullable=True)
    added_at = Column(DateTime, default=func.now(), nullable=False)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("TelegramSession", back_populates="channels")
    indexing_logs = relationship("IndexingLog", back_populates="channel")
    
    def __repr__(self):
        return f"<MonitoredChannel(id={self.id}, username='{self.username}', indexed={self.total_indexed})>"


class IndexingLog(Base):
    """
    Tracks indexing operations for debugging and analytics
    
    Records every message processed, AI token usage, and errors
    """
    __tablename__ = "indexing_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("monitored_channels.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    document_id = Column(String(255), unique=True, nullable=True, index=True)  # Meilisearch doc ID
    category = Column(String(50), nullable=True)
    subcategory = Column(String(50), nullable=True)
    indexed_at = Column(DateTime, default=func.now(), nullable=False)
    router_tokens = Column(Integer, nullable=True)  # AI cost tracking
    specialist_tokens = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)  # success, failed, skipped
    error_message = Column(Text, nullable=True)
    
    # Relationships
    channel = relationship("MonitoredChannel", back_populates="indexing_logs")
    
    def __repr__(self):
        return f"<IndexingLog(id={self.id}, channel_id={self.channel_id}, message_id={self.message_id}, status='{self.status}')>"


class SearchAnalytics(Base):
    """
    Tracks user searches for improvement and analytics
    
    Helps understand user behavior and improve search quality
    """
    __tablename__ = "search_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    query_text = Column(Text, nullable=False)
    detected_category = Column(String(50), nullable=True)
    filters_applied = Column(JSONB, nullable=True)  # Extracted filters as JSON
    results_count = Column(Integer, nullable=True)
    clicked_result = Column(String(255), nullable=True)  # Which result they clicked
    searched_at = Column(DateTime, default=func.now(), nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SearchAnalytics(id={self.id}, user_id={self.user_id}, query='{self.query_text[:30]}...')>"
