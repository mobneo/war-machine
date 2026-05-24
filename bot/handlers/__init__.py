from aiogram import Router

from bot.handlers import start, orders, positions, strategy, commands

router = Router()

router.include_router(start.router)
router.include_router(orders.router)
router.include_router(positions.router)
router.include_router(strategy.router)
router.include_router(commands.router)
