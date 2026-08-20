"""
Authentication middleware.

Runs on every incoming update.  Responsibilities:
1. Extract the Telegram user from the update.
2. Upsert a User record in the database.
3. Inject the User and a database session into handler data.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.database.connection import get_db_session
from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware that authenticates the Telegram user and injects:
        - ``db_session``: the async SQLAlchemy session for this request.
        - ``current_user``: the resolved User ORM instance.

    Handler functions can declare these as parameters:

        async def my_handler(message: Message, current_user: User, ...):
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Extract the Telegram user from the update
        telegram_user = None
        if isinstance(event, Update):
            if event.message:
                telegram_user = event.message.from_user
            elif event.callback_query:
                telegram_user = event.callback_query.from_user
            elif event.edited_message:
                telegram_user = event.edited_message.from_user

        # If we can't identify the user, pass through without injection
        if telegram_user is None:
            return await handler(event, data)

        async with get_db_session() as session:
            auth = AuthService(session)
            user = await auth.get_or_create_user(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )

            data["db_session"] = session
            data["current_user"] = user

            return await handler(event, data)
