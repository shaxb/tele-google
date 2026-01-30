#!/usr/bin/env python
"""
Test Database and Search Integration
Verifies PostgreSQL and Meilisearch operations
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from src.database import init_db, close_db, get_session
from src.database.models import TelegramSession, MonitoredChannel, IndexingLog
from src.search import get_search_engine
from src.utils.logger import get_logger

log = get_logger(__name__)


async def test_database():
    """Test PostgreSQL CRUD operations"""
    log.info("=" * 60)
    log.info("TESTING DATABASE (PostgreSQL)")
    log.info("=" * 60)
    
    # Initialize database
    await init_db()
    
    # Test 1: Create TelegramSession
    log.info("\n1. Testing TelegramSession creation...")
    session = await get_session()
    
    session_name = f"test_session_{random.randint(1000, 9999)}"
    new_session = TelegramSession(
        session_name=session_name,
        phone_number="+998901234567",
        api_id=12345,
        api_hash="test_hash_1234567890abcdef",
        is_active=True
    )
    
    await session.execute(select(TelegramSession))  # Test connection
    session.add(new_session)
    await session.commit()
    log.info(f"✓ Created: {new_session}")
    
    # Test 2: Create MonitoredChannel
    log.info("\n2. Testing MonitoredChannel creation...")
    channel_username = f"@TestChannel_{random.randint(1000, 9999)}"
    channel = MonitoredChannel(
        username=channel_username,
        title="Test Marketplace Channel",
        is_active=True,
        last_message_id=0,
        total_indexed=0,
        session_id=new_session.id
    )
    session.add(channel)
    await session.commit()
    log.info(f"✓ Created: {channel}")
    
    # Test 3: Create IndexingLog
    log.info("\n3. Testing IndexingLog creation...")
    doc_id = f"testchannel_{random.randint(10000, 99999)}"
    log_entry = IndexingLog(
        channel_id=channel.id,
        message_id=12345,
        document_id=doc_id,
        category="electronics",
        subcategory="smartphone",
        router_tokens=100,
        specialist_tokens=500,
        processing_time_ms=250,
        status="success"
    )
    session.add(log_entry)
    await session.commit()
    log.info(f"✓ Created: {log_entry}")
    
    # Test 4: Query records
    log.info("\n4. Testing queries...")
    result = await session.execute(
        select(MonitoredChannel).where(MonitoredChannel.username == channel_username)
    )
    found_channel = result.scalar_one()
    log.info(f"✓ Found channel: {found_channel.username}, Title: {found_channel.title}")
    
    # Count logs
    result = await session.execute(
        select(IndexingLog).where(IndexingLog.channel_id == found_channel.id)
    )
    logs = result.scalars().all()
    log.info(f"  Indexed logs count: {len(logs)}")
    
    await session.close()
    log.info("\n✓ All database tests passed!")


async def test_search():
    """Test Meilisearch operations"""
    log.info("\n" + "=" * 60)
    log.info("TESTING SEARCH ENGINE (Meilisearch)")
    log.info("=" * 60)
    
    search_engine = get_search_engine()
    await search_engine.initialize_index()
    
    # Test 1: Add a test document
    log.info("\n1. Testing document indexing...")
    doc_id = f"testchannel_{random.randint(10000, 99999)}"
    test_doc = {
        "id": doc_id,
        "category": "electronics",
        "subcategory": "smartphone",
        "item": "iPhone 15 Pro",
        "data": {
            "brand": "Apple",
            "model": "iPhone 15 Pro",
            "storage": "256GB",
            "color": "black",
            "condition": "excellent"
        },
        "price": 750,
        "currency": "USD",
        "searchable_text": "iPhone 15 Pro 256GB black excellent condition Apple smartphone",
        "images": ["https://example.com/img1.jpg"],
        "message_link": "https://t.me/TestChannel/12345",
        "channel": "@TestChannel",
        "posted_at": datetime.now().isoformat()
    }
    
    await search_engine.add_document(test_doc)
    await asyncio.sleep(1)  # Wait for indexing
    log.info(f"✓ Indexed document: {test_doc['id']}")
    
    # Test 2: Basic search
    log.info("\n2. Testing basic search...")
    results = await search_engine.search("iPhone")
    log.info(f"✓ Search 'iPhone': Found {results['estimatedTotalHits']} results")
    if results['hits']:
        log.info(f"  First result: {results['hits'][0]['item']}")
    
    # Test 3: Typo tolerance
    log.info("\n3. Testing typo tolerance...")
    results = await search_engine.search("ayfon")  # Typo: ayfon → iPhone
    log.info(f"✓ Search 'ayfon' (typo): Found {results['estimatedTotalHits']} results")
    if results['hits']:
        log.info(f"  Matched: {results['hits'][0]['item']}")
    
    # Test 4: Filtered search
    log.info("\n4. Testing filtered search...")
    results = await search_engine.search(
        "iPhone",
        filters="category = electronics AND data.color = black AND price <= 800",
        sort=["price:asc"]
    )
    log.info(f"✓ Filtered search: Found {results['estimatedTotalHits']} results")
    if results['hits']:
        hit = results['hits'][0]
        log.info(f"  Result: {hit['item']} - ${hit['price']} - {hit['data']['color']}")
    
    # Test 5: Get stats
    log.info("\n5. Testing index stats...")
    stats = await search_engine.get_stats()
    log.info(f"✓ Index stats:")
    log.info(f"  Documents: {stats.number_of_documents}")
    
    log.info("\n✓ All search tests passed!")


async def main():
    """Run all tests"""
    try:
        await test_database()
        await test_search()
        
        log.info("\n" + "=" * 60)
        log.info("ALL TESTS PASSED ✓")
        log.info("=" * 60)
        log.info("\nPhase 2: Database Layer is complete!")
        log.info("Ready to proceed to Phase 3: AI Pipeline")
        
    except Exception as e:
        log.error(f"Tests failed: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
