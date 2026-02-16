import asyncio
import logging

import src.core.logging_setup
from src.core.commands import set_default_commands
from src.core.config import settings
from src.core.setup import create_bot, create_dispatcher

logger = logging.getLogger(__name__)


async def on_startup():
    pass


async def on_shutdown():
    pass


async def main():
    logger.info("Starting polling...")

    bot = create_bot()
    dp = create_dispatcher()
    logger.info(bot.session.proxy)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await set_default_commands(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "update",
                "error",
                "my_chat_member",
                # "edited_message",
                # "channel_post",
                # "edited_channel_post",
                # "inline_query",
                # "chosen_inline_result",
                # "shipping_query",
                # "pre_checkout_query",
                # "poll",
                # "poll_answer",
                # "chat_member",
                # "chat_join_request",
            ],
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
