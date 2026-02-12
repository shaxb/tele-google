"""
Database package for Tele-Google
Schema-Free Adaptive Architecture (v2.0)
"""
from src.database.connection import init_db, close_db, get_session
from src.database.models import (
    TelegramSession,
    MonitoredChannel,
    Listing,
    SearchAnalytics,
    Base
)

__all__ = [
    "init_db", 
    "close_db",
    "get_session",
    "TelegramSession",
    "MonitoredChannel",
    "Listing",
    "SearchAnalytics",
    "Base"
]
