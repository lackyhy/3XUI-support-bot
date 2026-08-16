from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import config

class AdminMiddleware(BaseMiddleware):
    """
    Middleware that enforces authorization strictly to config.ADMIN_ID.
    All unauthorized users will be denied access.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return

        if user.id != config.ADMIN_ID:
            if isinstance(event, Message):
                await event.answer(
                    f"⛔ **Доступ запрещен!**\n\n"
                    f"Этот бот предназначен исключительно для одного администратора (`ID: {config.ADMIN_ID}`).\n"
                    f"Ваш ID: `{user.id}`",
                    parse_mode="Markdown"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещен!", show_alert=True)
            return

        return await handler(event, data)
