import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from bot.handlers import start

# Configure logging
logging.basicConfig(level=logging.INFO)


async def main():
    """Main bot entry point"""
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    # Initialize Bot with default properties
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Initialize Dispatcher
    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)

    # Start polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
