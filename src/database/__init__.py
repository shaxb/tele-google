"""
Database package for Tele-Google
Handles PostgreSQL connections and models
"""
from src.database.connection import get_db, init_db, close_db, get_session
from src.database.models import (
    TelegramSession,
    MonitoredChannel,
    IndexingLog,
    SearchAnalytics,
    Base
)

__all__ = [
    "get_db",
    "init_db", 
    "close_db",
    "get_session",
    "TelegramSession",
    "MonitoredChannel",
    "IndexingLog",
    "SearchAnalytics",
    "Base"
]
