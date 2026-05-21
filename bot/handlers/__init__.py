from aiogram import Router

from bot.handlers import start, orders, positions

router = Router()

router.include_router(start.router)
router.include_router(orders.router)
router.include_router(positions.router)
