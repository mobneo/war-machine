from aiogram import Router

from bot.handlers import start, orders

router = Router()

router.include_router(start.router)
router.include_router(orders.router)
