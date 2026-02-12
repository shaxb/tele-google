# Telegram Crawler - Monitor channels and index listings
# Pipeline: Extract text → Check duplicate → is_listing? → Embed → Store
# Watches channels.txt for hot-reload

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from telethon import TelegramClient, events
from telethon.tl.types import Message as TelegramMessage

from src.ai_parser import get_ai_parser
from src.config import get_config
from src.database.connection import init_db
from src.database.repository import ChannelRepository, ListingRepository, SessionRepository
from src.embeddings import get_embedding_generator


class TelegramCrawler:
    
    def __init__(self):
        self.config = get_config()
        self.clients: List[TelegramClient] = []
        self.active_channels: Set[str] = set()
        self.ai_parser = get_ai_parser()
        self.embedding_gen = get_embedding_generator()
        
        # Channels file watching
        self.channels_file = Path("channels.txt")
        self.channels_file_mtime = 0.0
        
        # Create required directories
        self.sessions_dir = Path("data/sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Telegram Crawler initialized")
    
    async def _create_and_auth_client(self, session_path: str, api_id: int, api_hash: str, phone: str) -> TelegramClient:
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.start(phone=phone)  # type: ignore[misc]
        return client
    
    async def initialize_clients(self) -> None:
        db_sessions = await SessionRepository.get_all_active()
        
        if not db_sessions:
            logger.info("Creating default session from .env config")
            client = await self._create_and_auth_client(
                str(self.sessions_dir / "default_session"),
                self.config.telegram.api_id,
                self.config.telegram.api_hash,
                self.config.telegram.phone
            )
            self.clients.append(client)
            logger.success("Default session authenticated")
        else:
            for db_session in db_sessions:
                client = await self._create_and_auth_client(
                    str(self.sessions_dir / db_session.session_name),
                    db_session.api_id,  # type: ignore[arg-type]
                    db_session.api_hash,  # type: ignore[arg-type]
                    db_session.phone_number  # type: ignore[arg-type]
                )
                self.clients.append(client)
                logger.success(f"Session '{db_session.session_name}' authenticated")
        
        logger.info(f"Total active clients: {len(self.clients)}")
    
    def load_monitored_channels(self) -> List[str]:
        if not self.channels_file.exists():
            logger.warning(f"{self.channels_file} not found, creating empty file")
            self.channels_file.write_text("# Add channels here, one per line\n# Example: @MalikaBozor\n")
            return []
        
        channels = []
        for line in self.channels_file.read_text().strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith('@'):
                    line = '@' + line
                channels.append(line)
        
        self.channels_file_mtime = os.path.getmtime(self.channels_file)
        logger.info(f"Loaded {len(channels)} channels from {self.channels_file}")
        return channels
    
    def channels_file_changed(self) -> bool:
        if not self.channels_file.exists():
            return False
        current_mtime = os.path.getmtime(self.channels_file)
        return current_mtime > self.channels_file_mtime
    
    async def join_channels(self) -> None:
        if not self.clients:
            logger.error("No clients available")
            return
        
        channels = self.load_monitored_channels()
        if not channels:
            logger.warning("No channels to monitor")
            return
        
        for idx, channel_username in enumerate(channels):
            client_idx = idx % len(self.clients)
            client = self.clients[client_idx]
            
            try:
                await client.get_entity(channel_username)
                self.active_channels.add(channel_username)
                logger.success(f"Joined {channel_username} (session {client_idx + 1}/{len(self.clients)})")
            except Exception as e:
                logger.error(f"Failed to join {channel_username}: {e}")
    
    async def _get_channel_id(self, event: events.NewMessage.Event) -> Optional[str]:
        chat = await event.get_chat()
        if not chat:
            return None
        
        if hasattr(chat, 'username') and chat.username:
            username = chat.username
            return f"@{username}" if not username.startswith('@') else username
        
        if hasattr(chat, 'id'):
            return str(chat.id)
        
        return None
    
    async def process_message(self, event: events.NewMessage.Event) -> None:
        """Pipeline: text → duplicate check → is_listing? → embed → store"""
        message: TelegramMessage = event.message
        
        channel_id = await self._get_channel_id(event)
        if not channel_id:
            return
        
        raw_text = message.message or ""
        if not raw_text.strip():
            return
        
        if await ListingRepository.exists(channel_id, message.id):
            logger.debug(f"Skipping duplicate: {channel_id}/{message.id}")
            return
        
        logger.info(f"Processing message {message.id} from {channel_id}")
        
        try:
            # Check if this is a listing
            if not self.ai_parser.is_listing(raw_text):
                return
            
            # Generate embedding
            embedding = self.embedding_gen.generate_embedding(raw_text)
            if not embedding:
                return
            
            # Store in PostgreSQL
            msg_date = message.date.replace(tzinfo=None) if message.date else datetime.utcnow()
            await ListingRepository.create(
                source_channel=channel_id,
                source_message_id=message.id,
                raw_text=raw_text,
                has_media=bool(message.media),
                embedding=embedding,
                created_at=msg_date
            )
            
            # Update channel stats
            await ChannelRepository.update_stats(channel_id, message.id)
            
            logger.success(f"✅ Message {message.id} indexed from {channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to process message {message.id}: {type(e).__name__}", exc_info=True)
    
    async def reload_channels(self) -> None:
        if not self.channels_file_changed():
            return
        
        logger.info("Channels file changed, reloading...")
        new_channels = set(self.load_monitored_channels())
        added_channels = new_channels - self.active_channels
        removed_channels = self.active_channels - new_channels
        
        if removed_channels:
            logger.info(f"Removed channels: {removed_channels}")
            self.active_channels -= removed_channels
        
        if not added_channels:
            return
        
        logger.info(f"Adding {len(added_channels)} new channels")
        
        for channel_username in added_channels:
            client_idx = len(self.active_channels) % len(self.clients)
            client = self.clients[client_idx]
            
            try:
                entity = await client.get_entity(channel_username)
                
                @client.on(events.NewMessage(chats=[entity]))
                async def handler(event):
                    await self.process_message(event)
                
                self.active_channels.add(channel_username)
                logger.success(f"✅ Added {channel_username} (hot-reload)")
            except Exception as e:
                logger.error(f"Failed to add {channel_username}: {e}")
    
    async def start_monitoring(self) -> None:
        if not self.clients:
            logger.error("No clients initialized")
            return
        
        for client in self.clients:
            @client.on(events.NewMessage(chats=list(self.active_channels)))
            async def handler(event):
                await self.process_message(event)
        
        logger.success(f"Monitoring {len(self.active_channels)} channels with {len(self.clients)} client(s)")
        logger.info(f"Watching {self.channels_file} for changes (checks every 30s)")
        
        async def file_watcher():
            while True:
                await asyncio.sleep(30)
                try:
                    await self.reload_channels()
                except Exception as e:
                    logger.error(f"Reload error: {e}")
        
        await asyncio.gather(
            *[client.run_until_disconnected() for client in self.clients],  # type: ignore[misc]
            file_watcher(),
            return_exceptions=True
        )
    
    async def backfill_channel(self, channel_username: str, limit: Optional[int] = None, min_id: int = 0) -> int:
        if not self.clients:
            return 0
        
        client = self.clients[0]
        indexed_count = 0
        
        logger.info(f"Backfilling {channel_username} (limit: {limit or 'unlimited'}, min_id: {min_id})")
        
        try:
            entity = await client.get_entity(channel_username)  # type: ignore[arg-type]
            msg_limit = limit if limit is not None else 100
            
            class MessageEvent:
                def __init__(self, msg: TelegramMessage, chat: Any):
                    self.message = msg
                    self._chat = chat
                async def get_chat(self) -> Any:
                    return self._chat
            
            async for message in client.iter_messages(entity, limit=msg_limit, min_id=min_id):  # type: ignore[arg-type]
                if message.message and message.message.strip():
                    event = MessageEvent(message, entity)  # type: ignore[arg-type]
                    await self.process_message(event)  # type: ignore[arg-type]
                    indexed_count += 1
                    await asyncio.sleep(0.5)
            
            logger.success(f"Backfill complete: {indexed_count} messages from {channel_username}")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Backfill failed: {e}", exc_info=True)
            return indexed_count
    
    async def start(self) -> None:
        try:
            logger.info("=" * 80)
            logger.info("TELEGRAM CRAWLER - Starting")
            logger.info("=" * 80)
            
            await init_db()
            await self.initialize_clients()
            await self.join_channels()
            await self.start_monitoring()
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.stop()
        except Exception as e:
            logger.error(f"Crawler failed: {e}", exc_info=True)
            await self.stop()
    
    async def stop(self):
        logger.info("Disconnecting clients...")
        for client in self.clients:
            await client.disconnect()  # type: ignore[misc]
        logger.success("Disconnected")


async def main():
    crawler = TelegramCrawler()
    await crawler.start()


if __name__ == "__main__":
    asyncio.run(main())
