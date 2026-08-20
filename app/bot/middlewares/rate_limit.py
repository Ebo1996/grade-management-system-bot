"""
Rate-limiting middleware.

Implements a simple per-user token-bucket approach using an in-memory
dictionary. This is sufficient for a single-process deployment.

For multi-process deployments, replace with Redis-backed rate limiting.
"""
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# {telegram_user_id: [timestamp, timestamp, ...]}
_request_timestamps: dict[int, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseMiddleware):
    """
    Limits each Telegram user to `max_requests` per 60-second sliding window.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._max_requests = self._settings.rate_limit_per_minute
        self._window = 60.0  # seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        user_id = self._extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        window_start = now - self._window

        # Prune old timestamps
        timestamps = _request_timestamps[user_id]
        _request_timestamps[user_id] = [t for t in timestamps if t > window_start]

        if len(_request_timestamps[user_id]) >= self._max_requests:
            logger.warning("rate_limit_exceeded", telegram_user_id=user_id)
            # Attempt to notify the user
            if event.message:
                await event.message.answer(
                    "⏳ You are sending too many requests. Please slow down."
                )
            return None  # Drop the update

        _request_timestamps[user_id].append(now)
        return await handler(event, data)

    @staticmethod
    def _extract_user_id(event: Update) -> int | None:
        if event.message and event.message.from_user:
            return event.message.from_user.id
        if event.callback_query and event.callback_query.from_user:
            return event.callback_query.from_user.id
        return None
