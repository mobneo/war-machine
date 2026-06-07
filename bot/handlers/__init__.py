import re

from aiogram import Router, F
from aiogram.types import Message

from bot.handlers import start, orders, positions, strategy, commands
from bot.services.strategy_service import StrategyService
from config.strategy import get_strategy_config

router = Router()

router.include_router(start.router)
router.include_router(orders.router)
router.include_router(positions.router)
router.include_router(strategy.router)
router.include_router(commands.router)

SIGNAL_PATTERN = re.compile(
    r'^(\S+)\s*>>>>>\s*(\S+)\s*>>>>>\s*(\S+)\s*>>>>>\s*(long|short)$',
    re.IGNORECASE,
)

signal_router = Router()
router.include_router(signal_router)


@signal_router.message(F.text.regexp(SIGNAL_PATTERN))
async def handle_signal(message: Message):
    """Handle trading signals in format: TYPE >>>>> GRADE >>>>> SYMBOL >>>>> SIDE"""
    match = SIGNAL_PATTERN.match(message.text.strip())
    if not match:
        return

    _signal_type, _grade, symbol_raw, side = match.groups()
    side = side.lower()
    symbol = symbol_raw.upper()
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"

    config = get_strategy_config(symbol)

    service = StrategyService()
    result = service.open_position_with_orders(symbol, side, config)

    if "error" in result:
        await message.answer(f"❌ Error: {result['error']}")
        return

    entry_price = result.get("entry_price", 0)
    position_size = result.get("position_size", 0)
    leverage = result.get("leverage", 0)
    stop_price = result.get("stop_price", 0)

    tp_pct = config.tp_percent * 100
    sl_pct = config.sl_percent * 100

    msg = (
        f"<b>🚀 Position opened!</b>\n\n"
        f"<code>{symbol}</code> <b>{side.upper()}</b>\n"
        f"  Entry: {entry_price:.2f}\n"
        f"  Size: {position_size:.4f}\n"
        f"  Leverage: {leverage}x\n"
        f"  SL: {stop_price:.2f}\n\n"
        f"  TP: {tp_pct:.1f}% | SL: {sl_pct:.1f}%"
    )
    await message.answer(msg)

    tp_orders = result.get("tp_orders", [])
    if tp_orders:
        tp_msg = "<b>✅ Take Profit orders:</b>\n"
        for i, tp in enumerate(tp_orders):
            tp_msg += f"  TP {i + 1}: {tp}\n"
        await message.answer(tp_msg)
