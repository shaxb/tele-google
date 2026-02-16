"""Admin-only bot commands: channel management, backfill, and system observability."""

import asyncio
import json
import shutil
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select, func, delete, case, text

from src.config import get_config
from src.database import get_session
from src.database.models import Listing, User
from src.database.repository import ChannelRepository
from src.utils.channels import load_channels, save_channels

router = Router(name="admin")
config = get_config()

# State for /auth flow  — stores pending auth per admin user
_auth_state: Dict[int, dict] = {}


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def admin_only(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user or message.from_user.id not in config.bot.admin_user_ids:
            await message.answer("❌ Admin only.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Backfill helper (reuses the existing authenticated session)
# ---------------------------------------------------------------------------

async def _run_backfill(channel_username: str, limit: int = 50) -> int:
    from telethon import TelegramClient
    from src.crawler import TelegramCrawler

    src_session = Path("data/sessions/default_session.session")
    if not src_session.exists():
        raise RuntimeError("No Telegram session found — authenticate on the server first")

    # Copy the session file so we don't conflict with the crawler's SQLite lock
    tmp_session = Path("data/sessions/_backfill_tmp")
    shutil.copy2(src_session, tmp_session.with_suffix(".session"))

    client = TelegramClient(str(tmp_session), config.telegram.api_id, config.telegram.api_hash)
    await client.connect()  # type: ignore[misc]
    if not await client.is_user_authorized():  # type: ignore[misc]
        raise RuntimeError("Telegram session expired — re-authenticate on the server")

    crawler = TelegramCrawler()
    crawler.clients = [client]
    try:
        return await crawler.backfill_channel(channel_username, limit=limit)
    finally:
        await client.disconnect()  # type: ignore[misc]
        # Clean up temp session files
        for ext in (".session", ".session-journal"):
            tmp_session.with_suffix(ext).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@router.message(Command("addchannel"))
@admin_only
async def cmd_add_channel(message: Message):
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📝 <b>Usage:</b> <code>/addchannel @channelname</code>")
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"

    current = load_channels()
    if channel in current:
        await message.answer(f"ℹ️ {channel} is already monitored.")
        return

    status = await message.answer(f"⏳ Adding {channel} and backfilling 50 messages…")
    try:
        current.append(channel)
        save_channels(current)
        indexed = await _run_backfill(channel, limit=50)
        await status.edit_text(
            f"✅ <b>Channel added!</b>\n\n"
            f"📊 {channel}\n📥 Indexed: {indexed} messages\n"
            f"🔄 Crawler will pick it up automatically."
        )
        logger.success(f"Admin {message.from_user.id} added {channel} ({indexed} msgs)")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Failed to add {channel}: {e}")
        await status.edit_text(f"❌ Failed to add channel\n\n<code>{_esc(e)}</code>")


@router.message(Command("removechannel"))
@admin_only
async def cmd_remove_channel(message: Message):
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b> <code>/removechannel @channelname</code>\n"
            "⚠️ This deletes all listings from this channel!"
        )
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"

    current = load_channels()
    if channel not in current:
        await message.answer(f"ℹ️ {channel} is not monitored.")
        return

    status = await message.answer(f"⏳ Removing {channel}…")
    try:
        async with get_session() as session:
            count = (await session.execute(
                select(func.count()).select_from(Listing).where(Listing.source_channel == channel)
            )).scalar() or 0

        current.remove(channel)
        save_channels(current)
        await ChannelRepository.deactivate(channel)

        async with get_session() as session:
            await session.execute(delete(Listing).where(Listing.source_channel == channel))
            await session.commit()

        await status.edit_text(
            f"✅ <b>Channel removed!</b>\n\n📊 {channel}\n🗑️ Deleted: {count} listings"
        )
        logger.success(f"Admin {message.from_user.id} removed {channel} ({count} listings)")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Failed to remove {channel}: {e}")
        await status.edit_text(f"❌ Failed to remove channel\n\n<code>{_esc(e)}</code>")


@router.message(Command("listchannels"))
@admin_only
async def cmd_list_channels(message: Message):
    status = await message.answer("⏳ Loading…")
    try:
        channels = load_channels()
        if not channels:
            await status.edit_text("📝 No channels monitored.")
            return

        stats: List[tuple] = []
        async with get_session() as session:
            for ch in channels:
                count = (await session.execute(
                    select(func.count()).select_from(Listing).where(Listing.source_channel == ch)
                )).scalar() or 0
                stats.append((ch, count))

        total = sum(c for _, c in stats)
        lines = [f"📊 <b>Channels ({len(channels)})</b>\n"]
        for ch, count in sorted(stats, key=lambda x: x[1], reverse=True):
            lines.append(f"• {ch}: <b>{count}</b>")
        lines.append(f"\n📈 Total: {total} listings")

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Failed to list channels: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("backfill"))
@admin_only
async def cmd_backfill(message: Message):
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b> <code>/backfill @channel [limit]</code>\n"
            "Default limit: 50"
        )
        return

    channel = parts[1].strip()
    if not channel.startswith("@"):
        channel = f"@{channel}"
    limit = int(parts[2]) if len(parts) > 2 else 50
    if not 1 <= limit <= 1000:
        await message.answer("❌ Limit must be 1–1000")
        return

    status = await message.answer(f"⏳ Backfilling {channel} ({limit} msgs)…")
    try:
        indexed = await _run_backfill(channel, limit=limit)
        await status.edit_text(f"✅ <b>Backfill done!</b>\n\n📊 {channel}\n📥 Indexed: {indexed}/{limit}")
        logger.success(f"Admin {message.from_user.id} backfilled {channel} ({indexed}/{limit})")  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Backfill failed for {channel}: {e}")
        await status.edit_text(f"❌ Backfill failed\n\n<code>{_esc(e)}</code>")


def _esc(e: Exception) -> str:
    """Escape HTML in error messages for Telegram."""
    return str(e)[:200].replace("<", "&lt;").replace(">", "&gt;")


def _esc_str(s: str) -> str:
    """Escape arbitrary string for HTML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Observability commands
# ---------------------------------------------------------------------------

@router.message(Command("stats"))
@admin_only
async def cmd_stats(message: Message):
    """System overview: totals, metadata coverage, categories, channels."""
    status = await message.answer("⏳ Gathering stats…")
    try:
        async with get_session() as session:
            # Total listings
            total = (await session.execute(
                select(func.count()).select_from(Listing)
            )).scalar() or 0

            # Listings with price
            with_price = (await session.execute(
                select(func.count()).select_from(Listing).where(Listing.price.isnot(None))
            )).scalar() or 0

            # Listings with metadata
            with_meta = (await session.execute(
                select(func.count()).select_from(Listing).where(Listing.item_metadata.isnot(None))
            )).scalar() or 0

            # Category breakdown (from JSONB)
            cat_rows = (await session.execute(
                select(
                    Listing.item_metadata["category"].astext.label("cat"),
                    func.count().label("cnt"),
                )
                .where(Listing.item_metadata.isnot(None))
                .group_by(text("cat"))
                .order_by(text("cnt DESC"))
                .limit(10)
            )).all()

            # Currency breakdown
            cur_rows = (await session.execute(
                select(Listing.currency, func.count().label("cnt"))
                .where(Listing.currency.isnot(None))
                .group_by(Listing.currency)
                .order_by(text("cnt DESC"))
            )).all()

            # Price stats
            price_stats = (await session.execute(
                select(
                    func.min(Listing.price),
                    func.max(Listing.price),
                    func.avg(Listing.price),
                ).where(Listing.price.isnot(None))
            )).one()

            # Channel breakdown
            ch_rows = (await session.execute(
                select(Listing.source_channel, func.count().label("cnt"))
                .group_by(Listing.source_channel)
                .order_by(text("cnt DESC"))
            )).all()

            # User count
            user_count = (await session.execute(
                select(func.count()).select_from(User)
            )).scalar() or 0

            # Search count
            search_count = (await session.execute(
                select(func.count()).select_from(text("search_analytics"))
            )).scalar() or 0

        lines = [
            f"📊 <b>System Stats</b>\n",
            f"📦 Total listings: <b>{total}</b>",
            f"🏷️ With metadata: <b>{with_meta}</b> ({_pct(with_meta, total)})",
            f"💰 With price: <b>{with_price}</b> ({_pct(with_price, total)})",
            f"👥 Users: <b>{user_count}</b>",
            f"🔍 Searches: <b>{search_count}</b>",
        ]

        if price_stats[0] is not None:
            lines.append(f"\n💵 <b>Price range:</b> {price_stats[0]:,.0f} – {price_stats[1]:,.0f}")
            lines.append(f"📏 Avg price: {price_stats[2]:,.0f}")

        if cur_rows:
            lines.append(f"\n💱 <b>Currencies:</b>")
            for cur, cnt in cur_rows:
                lines.append(f"  • {cur}: {cnt}")

        if cat_rows:
            lines.append(f"\n📂 <b>Categories:</b>")
            for cat, cnt in cat_rows:
                lines.append(f"  • {cat or 'unknown'}: {cnt}")

        if ch_rows:
            lines.append(f"\n📡 <b>By channel:</b>")
            for ch, cnt in ch_rows:
                lines.append(f"  • {ch}: {cnt}")

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("recent"))
@admin_only
async def cmd_recent(message: Message):
    """Show last N listings with extracted metadata."""
    if not message.text:
        return
    parts = message.text.split()
    limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
    limit = min(limit, 10)

    status = await message.answer("⏳ Loading recent listings…")
    try:
        async with get_session() as session:
            rows = (await session.execute(
                select(Listing)
                .order_by(Listing.created_at.desc())
                .limit(limit)
            )).scalars().all()

        if not rows:
            await status.edit_text("📭 No listings yet.")
            return

        lines = [f"🕐 <b>Last {len(rows)} listings</b>\n"]
        for listing in rows:
            meta = listing.item_metadata or {}
            title = meta.get("title", "—")
            category = meta.get("category", "—")
            price_str = f"{listing.price:,.0f} {listing.currency}" if listing.price else "—"  # type: ignore[arg-type]
            channel = listing.source_channel or "?"
            date = listing.created_at.strftime("%m/%d %H:%M") if listing.created_at else "?"  # type: ignore[union-attr]

            lines.append(
                f"<b>#{listing.id}</b> | {_esc_str(title)}\n"
                f"  📂 {category} | 💰 {price_str}\n"
                f"  📡 {channel} | 🕐 {date}"
            )

            # Show extra metadata keys (beyond the universal ones)
            extras = {k: v for k, v in meta.items()
                      if k not in ("title", "category", "price", "currency", "condition")}
            if extras:
                extra_str = ", ".join(f"{k}={v}" for k, v in list(extras.items())[:5])
                lines.append(f"  🔍 {_esc_str(extra_str)}")
            lines.append("")

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Recent failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("inspect"))
@admin_only
async def cmd_inspect(message: Message):
    """Show full details of a listing by ID."""
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("📝 <b>Usage:</b> <code>/inspect 123</code>")
        return

    listing_id = int(parts[1])
    status = await message.answer("⏳ Loading…")
    try:
        async with get_session() as session:
            listing = (await session.execute(
                select(Listing).where(Listing.id == listing_id)
            )).scalar_one_or_none()

        if not listing:
            await status.edit_text(f"❌ Listing #{listing_id} not found.")
            return

        meta = listing.item_metadata or {}  # type: ignore[assignment]
        meta_json = json.dumps(meta, ensure_ascii=False, indent=2) if meta else "null"  # type: ignore[arg-type]
        raw_text = str(listing.raw_text or "")[:500]

        lines = [
            f"🔎 <b>Listing #{listing.id}</b>\n",
            f"📡 Channel: {listing.source_channel}",
            f"💬 Message ID: {listing.source_message_id}",
            f"📷 Has media: {'yes' if listing.has_media else 'no'}",  # type: ignore[arg-type]
            f"🕐 Created: {listing.created_at}",
            f"💰 Price: {listing.price} {listing.currency or ''}",
            f"\n📝 <b>Raw text:</b>\n<pre>{_esc_str(raw_text)}</pre>",
            f"\n🏷️ <b>Metadata:</b>\n<pre>{_esc_str(meta_json)}</pre>",
        ]

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Inspect failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("health"))
@admin_only
async def cmd_health(message: Message):
    """Show system health: memory, swap, disk, uptime."""
    status = await message.answer("⏳ Checking system…")
    try:
        proc = await asyncio.create_subprocess_shell(
            "echo \"$(free -h | head -3)\" && echo '---' && "
            "df -h / | tail -1 && echo '---' && uptime",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode().strip()

        # Parse free output
        mem_lines = output.split("---")
        mem_info = mem_lines[0].strip() if len(mem_lines) > 0 else "?"
        disk_info = mem_lines[1].strip() if len(mem_lines) > 1 else "?"
        uptime_info = mem_lines[2].strip() if len(mem_lines) > 2 else "?"

        lines = [
            f"🏥 <b>System Health</b>\n",
            f"<pre>{_esc_str(mem_info)}</pre>",
            f"\n💾 <b>Disk:</b> <code>{_esc_str(disk_info)}</code>",
            f"⏰ <b>Uptime:</b> <code>{_esc_str(uptime_info)}</code>",
        ]

        await status.edit_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


def _pct(part: int, total: int) -> str:
    """Return percentage string."""
    return f"{part / total * 100:.0f}%" if total else "0%"


# ---------------------------------------------------------------------------
# Operational commands — /logs, /sql
# ---------------------------------------------------------------------------

@router.message(Command("logs"))
@admin_only
async def cmd_logs(message: Message):
    """Show recent log lines from a service."""
    if not message.text:
        return
    parts = message.text.split()
    service = parts[1] if len(parts) > 1 else "bot"
    n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20
    n = min(n, 50)

    if service not in ("bot", "crawler"):
        await message.answer("📝 <b>Usage:</b> <code>/logs bot|crawler [N]</code>")
        return

    status = await message.answer(f"⏳ Fetching {service} logs…")
    try:
        proc = await asyncio.create_subprocess_shell(
            f"journalctl -u tele-google-{service} --no-pager -n {n} --output=short-iso 2>/dev/null || "
            f"tail -n {n} logs/app.log 2>/dev/null || echo 'No logs available'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode().strip()

        # Truncate to fit Telegram's 4096 char limit
        if len(output) > 3800:
            output = output[-3800:]
            output = "…(truncated)\n" + output

        await status.edit_text(
            f"📋 <b>Logs: {service}</b> (last {n})\n\n<pre>{_esc_str(output)}</pre>"
        )
    except asyncio.TimeoutError:
        await status.edit_text("❌ Log fetch timed out")
    except Exception as e:
        logger.error(f"Logs command failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")


@router.message(Command("sql"))
@admin_only
async def cmd_sql(message: Message):
    """Run a read-only SQL query against the database."""
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📝 <b>Usage:</b> <code>/sql SELECT count(*) FROM listings</code>\n\n"
            "⚠️ Only SELECT queries allowed. Results truncated to 50 rows."
        )
        return

    query = parts[1].strip()

    # Security: only allow SELECT statements
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        await message.answer("❌ Only <code>SELECT</code> queries are allowed.")
        return
    # Block dangerous keywords
    for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT"):
        if keyword in normalized:
            await message.answer(f"❌ <code>{keyword}</code> is not allowed in read-only mode.")
            return

    status = await message.answer("⏳ Running query…")
    try:
        async with get_session() as session:
            result = await asyncio.wait_for(
                session.execute(text(query)),
                timeout=5.0,
            )
            rows = result.fetchmany(50)
            columns = list(result.keys()) if result.keys() else []

        if not rows:
            await status.edit_text("📭 Query returned 0 rows.")
            return

        # Format as simple table
        lines = [f"📊 <b>Results</b> ({len(rows)} rows)\n"]

        # Header
        header = " | ".join(str(c) for c in columns)
        lines.append(f"<pre>{_esc_str(header)}")
        lines.append("-" * min(len(header), 60))

        # Rows
        for row in rows:
            row_str = " | ".join(str(v)[:30] for v in row)
            lines.append(_esc_str(row_str))

        lines.append("</pre>")

        output = "\n".join(lines)
        if len(output) > 4000:
            output = output[:4000] + "\n…(truncated)"

        await status.edit_text(output)
    except asyncio.TimeoutError:
        await status.edit_text("❌ Query timed out (5s limit).")
    except Exception as e:
        logger.error(f"SQL command failed: {e}")
        await status.edit_text(f"❌ Query failed\n\n<code>{_esc(e)}</code>")


# ---------------------------------------------------------------------------
# Remote auth — /auth
# ---------------------------------------------------------------------------

@router.message(Command("auth"))
@admin_only
async def cmd_auth(message: Message):
    """Start remote Telegram authentication for the crawler account."""
    if not message.from_user:
        return

    parts = (message.text or "").split()

    # If user is replying with a code
    if len(parts) >= 2 and message.from_user.id in _auth_state:
        code = parts[1].strip()
        state = _auth_state.pop(message.from_user.id)
        client = state["client"]
        phone = state["phone"]
        phone_code_hash = state["phone_code_hash"]

        status = await message.answer("⏳ Signing in…")
        try:
            from telethon import TelegramClient
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            me = await client.get_me()
            name = getattr(me, "first_name", "Unknown")
            await client.disconnect()
            await status.edit_text(
                f"✅ <b>Authenticated as {_esc_str(name)}</b>\n\n"
                f"Session saved. Restart the crawler with <code>/restart crawler</code>"
            )
        except Exception as e:
            await client.disconnect()
            await status.edit_text(f"❌ Auth failed\n\n<code>{_esc(e)}</code>")
        return

    # Start new auth flow
    status = await message.answer("⏳ Sending verification code…")
    try:
        from telethon import TelegramClient
        sessions_dir = Path("data/sessions")
        sessions_dir.mkdir(parents=True, exist_ok=True)

        client = TelegramClient(
            str(sessions_dir / "default_session"),
            config.telegram.api_id,
            config.telegram.api_hash,
        )
        await client.connect()

        phone = config.telegram.phone
        result = await client.send_code_request(phone)

        _auth_state[message.from_user.id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": result.phone_code_hash,
        }

        masked = phone[:4] + "****" + phone[-2:]
        await status.edit_text(
            f"📱 Code sent to <b>{masked}</b>\n\n"
            f"Reply with: <code>/auth CODE</code>\n"
            f"Example: <code>/auth 12345</code>\n\n"
            f"⏱ Code expires in 5 minutes."
        )
    except Exception as e:
        logger.error(f"Auth command failed: {e}")
        await status.edit_text(f"❌ Failed to send code\n\n<code>{_esc(e)}</code>")


# ---------------------------------------------------------------------------
# Deploy & restart — /deploy, /restart
# ---------------------------------------------------------------------------

@router.message(Command("deploy"))
@admin_only
async def cmd_deploy(message: Message):
    """Pull latest code from git and restart all services."""
    status = await message.answer("🚀 <b>Deploying…</b>\n\n⏳ git pull…")
    try:
        # Step 1: git pull
        proc = await asyncio.create_subprocess_shell(
            "cd ~/tele-google && git pull origin master 2>&1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        git_output = stdout.decode().strip()

        await status.edit_text(
            f"🚀 <b>Deploying…</b>\n\n"
            f"✅ git pull:\n<pre>{_esc_str(git_output[:500])}</pre>\n\n"
            f"⏳ pip install…"
        )

        # Step 2: pip install
        proc = await asyncio.create_subprocess_shell(
            "cd ~/tele-google && source venv/bin/activate && pip install -r requirements.txt -q 2>&1 | tail -5",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        pip_output = stdout.decode().strip()

        await status.edit_text(
            f"🚀 <b>Deploying…</b>\n\n"
            f"✅ git pull: done\n"
            f"✅ pip: {_esc_str(pip_output[-200:]) if pip_output else 'ok'}\n\n"
            f"⏳ Restarting services…"
        )

        # Step 3: restart services
        proc = await asyncio.create_subprocess_shell(
            "sudo systemctl restart tele-google-crawler && "
            "sudo systemctl restart tele-google-bot",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)

        # Note: the bot process itself will be killed by systemctl restart,
        # so the user won't see this message unless the bot restarts fast enough.
        # This is expected behavior.
        await status.edit_text(
            "🚀 <b>Deploy complete!</b>\n\n"
            "✅ git pull\n"
            "✅ pip install\n"
            "✅ Services restarting\n\n"
            "Bot will be back in a few seconds."
        )
    except asyncio.TimeoutError:
        await status.edit_text("❌ Deploy timed out")
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        await status.edit_text(f"❌ Deploy failed\n\n<code>{_esc(e)}</code>")


@router.message(Command("restart"))
@admin_only
async def cmd_restart(message: Message):
    """Restart a specific service: /restart bot|crawler|all"""
    parts = (message.text or "").split()
    target = parts[1] if len(parts) > 1 else "all"

    if target not in ("bot", "crawler", "all"):
        await message.answer("📝 <b>Usage:</b> <code>/restart bot|crawler|all</code>")
        return

    status = await message.answer(f"⏳ Restarting <b>{target}</b>…")
    try:
        if target == "all":
            cmd = "sudo systemctl restart tele-google-crawler && sudo systemctl restart tele-google-bot"
        else:
            cmd = f"sudo systemctl restart tele-google-{target}"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode == 0:
            await status.edit_text(f"✅ <b>{target}</b> restarted successfully")
        else:
            await status.edit_text(f"❌ Restart failed\n\n<code>{_esc_str(stderr.decode()[:500])}</code>")
    except asyncio.TimeoutError:
        await status.edit_text("❌ Restart timed out")
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        await status.edit_text(f"❌ Error\n\n<code>{_esc(e)}</code>")
