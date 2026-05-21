from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.services.bybit_service import BybitService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    await message.answer(
        "👋 Hi! I'm a futures trading bot for Bybit.\n\n"
        "Available commands:\n"
        "/balance - show balance\n"
        "/positions - open positions\n"
        "/ticker &lt;symbol&gt; - asset price (e.g., /ticker BTCUSDT)\n"
        "/buy &lt;symbol&gt; &lt;amount&gt; - buy (for example, /buy BTCUSDT 0.001)\n"
        "/sell &lt;symbol&gt; &lt;amount&gt; - sell (for example, /sell BTCUSDT 0.001)"
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Handle /balance command"""
    service = BybitService()
    balance = service.get_balance("USDT")

    if 'error' in balance:
        await message.answer(f"❌ Error: {balance['error']}")
        return

    await message.answer(
        f"💰 Balance USDT:\n"
        f" available: {balance['free']:.2f}\n"
        f" frozen: {balance['used']:.2f}\n"
        f" total: {balance['total']:.2f}"
    )


@router.message(Command("positions"))
async def cmd_positions(message: Message):
    """Handle /positions command"""
    service = BybitService()
    positions = service.get_positions()

    if not positions:
        await message.answer("⚠️ There are no open positions")
        return

    # TODO: Implement proper position display
    await message.answer(f"📋 Open positions: {len(positions)} pcs.")


@router.message(Command("ticker"))
async def cmd_ticker(message: Message):
    """Handle /ticker <symbol> command"""
    symbol = message.get_args().strip().upper()

    if not symbol:
        await message.answer("⚠️ Enter a symbol: /ticker BTCUSDT")
        return

    service = BybitService()
    ticker = service.get_ticker(symbol)

    if not ticker:
        await message.answer(f"❌ Symbol not found: {symbol}")
        return

    if 'error' in ticker:
        await message.answer(f"❌ Error: {ticker['error']}")
        return

    await message.answer(
        f"📊 {symbol}:\n"
        f" last: {ticker['last']:.2f}\n"
        f" bid: {ticker['bid']:.2f}\n"
        f" ask: {ticker['ask']:.2f}\n"
        f" volume: {ticker['volume']:.4f}"
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Handle /buy <symbol> <amount> command"""
    args = message.get_args().strip().split()

    if len(args) != 2:
        await message.answer("⚠️ Usage: /buy <symbol> <amount>")
        return

    symbol, amount_str = args[0].upper(), args[1]

    try:
        amount = float(amount_str)
    except ValueError:
        await message.answer("❌ Incorrect quantity")
        return

    service = BybitService()
    order = service.create_market_order(symbol, "buy", amount)

    if 'error' in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Purchase order created!\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>price</code>: {order['price']}\n"
        f"<code>id</code>: {order['id']}"
    )


@router.message(Command("sell"))
async def cmd_sell(message: Message):
    """Handle /sell <symbol> <amount> command"""
    args = message.get_args().strip().split()

    if len(args) != 2:
        await message.answer("⚠️ Usage: /sell <symbol> <amount>")
        return

    symbol, amount_str = args[0].upper(), args[1]

    try:
        amount = float(amount_str)
    except ValueError:
        await message.answer("❌ Incorrect quantity")
        return

    service = BybitService()
    order = service.create_market_order(symbol, "sell", amount)

    if 'error' in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Sell order created!\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>price</code>: {order['price']}\n"
        f"<code>id</code>: {order['id']}"
    )
