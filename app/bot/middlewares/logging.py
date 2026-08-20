"""
Logging middleware.

Logs every incoming update for audit and debugging purposes.
Sensitive content (photo bytes, etc.) is never logged — only metadata.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log key metadata for each incoming Telegram update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        user_id: int | None = None
        update_type: str = "unknown"
        content_type: str = "unknown"

        if event.message:
            update_type = "message"
            content_type = event.message.content_type
            if event.message.from_user:
                user_id = event.message.from_user.id

        elif event.callback_query:
            update_type = "callback_query"
            content_type = event.callback_query.data or ""
            if event.callback_query.from_user:
                user_id = event.callback_query.from_user.id

        logger.debug(
            "update_received",
            update_id=event.update_id,
            update_type=update_type,
            content_type=content_type,
            telegram_user_id=user_id,
        )

        result = await handler(event, data)

        logger.debug(
            "update_processed",
            update_id=event.update_id,
            telegram_user_id=user_id,
        )

        return result
