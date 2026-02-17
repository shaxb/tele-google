"""Production notification system — structured events to a Telegram log channel.

Architecture:
- Singleton per process (bot and crawler each get their own instance)
- Fire-and-forget: never blocks or crashes the caller
- Rate-limited: internal queue with 1 msg/sec max to avoid Telegram throttling
- Error batching: groups errors, flushes a summary every 60s
- Optional: if LOG_CHANNEL_ID is not set, all methods are silent no-ops

Usage:
    notifier = get_notifier()
    await notifier.start()                    # Start background tasks
    await notifier.listing(...)               # Log a new listing
    notifier.count("messages_seen")           # Bump a pipeline metric
    await notifier.stop()                     # Cleanup on shutdown
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.config import get_config
from src.bot_utils.formatters import esc_html


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------

class Notifier:
    """Send structured events to a Telegram log channel."""

    def __init__(self) -> None:
        config = get_config()
        self._channel_id = config.bot.log_channel_id
        self._enabled = bool(self._channel_id)
        self._bot: Optional[Bot] = None
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._error_buffer: List[Dict[str, Any]] = []
        self._tasks: List[asyncio.Task] = []  # type: ignore[type-arg]
        self.metrics: Dict[str, int] = defaultdict(int)

        if self._enabled:
            self._bot = Bot(
                token=config.bot.token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start background consumer and error flusher."""
        if not self._enabled:
            return
        self._tasks = [
            asyncio.create_task(self._send_loop()),
            asyncio.create_task(self._error_flush_loop()),
        ]

    async def stop(self) -> None:
        """Drain queue, cancel tasks, close HTTP session."""
        for task in self._tasks:
            task.cancel()
        if self._bot:
            await self._bot.session.close()

    # ------------------------------------------------------------------
    # Internal send — queue-based, rate-limited
    # ------------------------------------------------------------------

    def _enqueue(self, text: str) -> None:
        """Non-blocking enqueue. Drops if queue is full (backpressure)."""
        if not self._enabled:
            return
        try:
            self._queue.put_nowait(text)
        except asyncio.QueueFull:
            logger.warning("Notifier queue full — dropping message")

    async def _send_loop(self) -> None:
        """Consumer: sends queued messages with rate limiting (1 msg/sec)."""
        while True:
            try:
                text = await self._queue.get()
                if self._bot and self._channel_id:
                    try:
                        await self._bot.send_message(self._channel_id, text[:4096])
                    except Exception as e:
                        logger.warning(f"Notifier send failed: {e}")
                await asyncio.sleep(1)  # Rate limit: max 1 msg/sec
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Notifier send loop error: {e}")
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Event methods — the public API
    # ------------------------------------------------------------------

    async def startup(self, service: str) -> None:
        """Service started."""
        self._enqueue(
            f"🟢 <b>{esc_html(service)}</b> started\n"
            f"🕐 {datetime.utcnow():%Y-%m-%d %H:%M UTC}"
        )

    async def shutdown(self, service: str) -> None:
        """Service stopping."""
        self._enqueue(
            f"🔴 <b>{esc_html(service)}</b> stopping\n"
            f"🕐 {datetime.utcnow():%Y-%m-%d %H:%M UTC}"
        )

    async def listing(
        self, channel: str, title: str, price: Any,
        currency: Optional[str], category: Optional[str],
        confidence: float = 0.0,
        processing_time_ms: int = 0,
        message_link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """New listing indexed — full pipeline traceability."""
        self.metrics["listings_indexed"] += 1
        try:
            price_str = f"{float(price):,.0f} {esc_html(str(currency or '?'))}" if price else "—"
        except (ValueError, TypeError):
            price_str = esc_html(str(price))
        cat = esc_html(str(category or "?"))
        link_line = f"  🔗 {message_link}\n" if message_link else ""

        # Format extra metadata fields (exclude universal ones already shown)
        extra = ""
        if metadata:
            skip = {"price", "currency", "category", "title", "condition"}
            extras = {k: v for k, v in metadata.items() if k not in skip and v is not None}
            if extras:
                extra = "  🧩 " + " | ".join(
                    f"{esc_html(str(k))}: {esc_html(str(v))}" for k, v in extras.items()
                ) + "\n"

        self._enqueue(
            f"📦 <b>{esc_html(title)}</b>\n"
            f"{link_line}"
            f"  💰 {price_str} | 📂 {cat} | 📡 {esc_html(str(channel))}\n"
            f"{extra}"
            f"  📊 {confidence:.0%} conf | ⏱ {processing_time_ms}ms"
        )

    async def error(self, context: str, err: Exception) -> None:
        """Buffer an error for batched notification (flushed every 60s)."""
        self.metrics["errors"] += 1
        self._error_buffer.append({
            "ctx": context,
            "err": str(err)[:200],
            "time": datetime.utcnow().strftime("%H:%M:%S"),
        })

    async def deal(
        self, title: str, price: float, currency: str,
        median: float, deviation: float,
    ) -> None:
        """Deal detected — item significantly below market."""
        pct = abs(deviation) * 100
        self._enqueue(
            f"🔥 <b>DEAL DETECTED</b>\n"
            f"  {esc_html(title)}\n"
            f"  💰 {price:,.0f} {esc_html(currency)} vs median {median:,.0f}\n"
            f"  📉 {pct:.0f}% below market"
        )

    async def search(
        self, user_id: int, query: str, results_count: int, response_time_ms: int,
    ) -> None:
        """User search executed."""
        emoji = "✅" if results_count > 0 else "⭕"
        self._enqueue(
            f"🔍 <b>Search</b> by <code>{user_id}</code>\n"
            f"  {emoji} {results_count} results in {response_time_ms}ms\n"
            f"  📝 {esc_html(query)}"
        )

    async def alert(self, message: str) -> None:
        """Operational alert — anomaly, threshold breach, etc."""
        self._enqueue(f"⚠️ <b>ALERT</b>\n{message}")

    async def health_report(self, report: str) -> None:
        """Send a pre-formatted health report."""
        self._enqueue(f"🏥 <b>Health Report</b>\n{report}")

    def count(self, key: str, n: int = 1) -> None:
        """Increment a pipeline metric (non-async, zero overhead)."""
        self.metrics[key] += n

    # ------------------------------------------------------------------
    # Error batching — flush grouped summary every 60s
    # ------------------------------------------------------------------

    async def _error_flush_loop(self) -> None:
        """Group errors and send a summary every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(60)
                if not self._error_buffer:
                    continue

                errors = self._error_buffer.copy()
                self._error_buffer.clear()

                if len(errors) == 1:
                    e = errors[0]
                    self._enqueue(
                        f"🔴 <b>Error</b> in {esc_html(e['ctx'])}\n"
                        f"  <code>{esc_html(e['err'])}</code>\n"
                        f"  🕐 {e['time']}"
                    )
                else:
                    # Group by context
                    groups: Dict[str, int] = defaultdict(int)
                    for e in errors:
                        groups[e["ctx"]] += 1
                    lines = [f"🔴 <b>{len(errors)} errors</b> in last 60s\n"]
                    for ctx, cnt in sorted(groups.items(), key=lambda x: -x[1]):
                        lines.append(f"  • {esc_html(ctx)}: {cnt}x")
                    # Show last error detail
                    last = errors[-1]
                    lines.append(f"\n  Last: <code>{esc_html(last['err'])}</code>")
                    self._enqueue("\n".join(lines))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Notifier error flush failed: {e}")


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_instance: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Get or create the process-wide Notifier singleton."""
    global _instance
    if _instance is None:
        _instance = Notifier()
    return _instance
