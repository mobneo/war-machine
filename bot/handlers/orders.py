from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

from bot.services.orders import OrderService

router = Router()


@router.message(Command("buy"))
async def cmd_buy(message: Message, command: CommandObject):
    """Handle /buy <symbol> <amount> command"""
    args = command.args.strip().split() if command.args else ""

    if len(args) != 2:
        await message.answer("⚠️ Usage: /buy <symbol> <amount>")
        return

    symbol, amount_str = args[0].upper(), args[1]

    try:
        amount = float(amount_str)
    except ValueError:
        await message.answer("❌ Incorrect quantity")
        return

    service = OrderService()
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
async def cmd_sell(message: Message, command: CommandObject):
    """Handle /sell <symbol> <amount> command"""
    # args = message.get_args().strip().split()
    args = command.args.strip().split() if command.args else ""

    if len(args) != 2:
        await message.answer("⚠️ Usage: /sell <symbol> <amount>")
        return

    symbol, amount_str = args[0].upper(), args[1]

    try:
        amount = float(amount_str)
    except ValueError:
        await message.answer("❌ Incorrect quantity")
        return

    service = OrderService()
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


# Stop-Loss commands
@router.message(Command("sl"))
async def cmd_stop_loss(message: Message, command: CommandObject):
    """Handle stop-loss orders
    Usage: /sl <symbol> <amount> <stop_price> [limit_price]
    Examples:
        /sl BTCUSDT 0.001 50000 - market stop-loss
        /sl BTCUSDT 0.001 50000 49500 - limit stop-loss
    """
    # args = message.get_args().strip().split()
    args = command.args.strip().split() if command.args else ""

    if len(args) < 3:
        await message.answer(
            "⚠️ Usage: /sl <symbol> <amount> <stop_price> [limit_price]\n"
            "Examples:\n"
            "/sl BTCUSDT 0.001 50000 - market stop-loss\n"
            "/sl BTCUSDT 0.001 50000 49500 - limit stop-loss"
        )
        return

    symbol, amount_str, stop_price_str = args[0].upper(), args[1], args[2]
    limit_price = float(args[3]) if len(args) > 3 else None

    try:
        amount = float(amount_str)
        stop_price = float(stop_price_str)
    except ValueError:
        await message.answer("❌ Incorrect values")
        return

    service = OrderService()

    if limit_price:
        order = service.create_stop_limit_order(
            symbol, "sell", amount, limit_price, stop_price, reduce_only=True
        )
        order_type = "stop-limit"
    else:
        order = service.create_stop_market_order(
            symbol, "sell", amount, stop_price, reduce_only=True
        )
        order_type = "stop-market"

    if 'error' in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Stop-Loss order created! ({order_type})\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>stop_price</code>: {order['stop_price']}\n"
        f"<code>limit_price</code>: {order.get('price', 'N/A')}\n"
        f"<code>id</code>: {order['id']}"
    )


# Take-Profit commands
@router.message(Command("tp"))
async def cmd_take_profit(message: Message, command: CommandObject):
    """Handle take-profit orders
    Usage: /tp <symbol> <amount> <trigger_price> [limit_price]
    Examples:
        /tp BTCUSDT 0.001 60000 - market take-profit
        /tp BTCUSDT 0.001 60000 60500 - limit take-profit
    """
    # args = message.get_args().strip().split()
    args = command.args.strip().split() if command.args else ""

    if len(args) < 3:
        await message.answer(
            "⚠️ Usage: /tp <symbol> <amount> <trigger_price> [limit_price]\n"
            "Examples:\n"
            "/tp BTCUSDT 0.001 60000 - market take-profit\n"
            "/tp BTCUSDT 0.001 60000 60500 - limit take-profit"
        )
        return

    symbol, amount_str, trigger_price_str = args[0].upper(), args[1], args[2]
    limit_price = float(args[3]) if len(args) > 3 else None

    try:
        amount = float(amount_str)
        trigger_price = float(trigger_price_str)
    except ValueError:
        await message.answer("❌ Incorrect values")
        return

    service = OrderService()

    if limit_price:
        order = service.create_take_profit_order(
            symbol, "sell", amount, trigger_price, order_type="limit", price=limit_price
        )
        order_type = "take-profit limit"
    else:
        order = service.create_take_profit_order(
            symbol, "sell", amount, trigger_price, order_type="market"
        )
        order_type = "take-profit market"

    if 'error' in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Take-Profit order created! ({order_type})\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>trigger_price</code>: {order['stop_price']}\n"
        f"<code>limit_price</code>: {order.get('price', 'N/A')}\n"
        f"<code>id</code>: {order['id']}"
    )


# Trailing Stop commands
@router.message(Command("trailing"))
async def cmd_trailing_stop(message: Message, command: CommandObject):
    """Handle trailing-stop orders
    Usage: /trailing <symbol> <amount> <trailing_distance> [limit_price]
    Trailing distance in % (e.g., 1 = 1%)
    Examples:
        /trailing BTCUSDT 0.001 1 - trailing stop with 1% distance, market order
        /trailing BTCUSDT 0.001 1 59000 - limit trailing stop
    """
    args = command.args.strip().split() if command.args else ""

    if len(args) < 3:
        await message.answer(
            "⚠️ Usage: /trailing <symbol> <amount> <trailing_distance> [limit_price]\n"
            "Trailing distance in % (e.g., 1 = 1%)\n"
            "Examples:\n"
            "/trailing BTCUSDT 0.001 1 - market trailing stop\n"
            "/trailing BTCUSDT 0.001 1 59000 - limit trailing stop"
        )
        return

    symbol, amount_str, trailing_str = args[0].upper(), args[1], args[2]
    limit_price = float(args[3]) if len(args) > 3 else None

    try:
        amount = float(amount_str)
        trailing_distance = float(trailing_str)
    except ValueError:
        await message.answer("❌ Incorrect values")
        return

    service = OrderService()

    if limit_price:
        order = service.create_trailing_stop_order(
            symbol, "sell", amount, trailing_distance,
            order_type="limit", price=limit_price
        )
        order_type = "trailing-stop limit"
    else:
        order = service.create_trailing_stop_order(
            symbol, "sell", amount, trailing_distance,
            order_type="market"
        )
        order_type = "trailing-stop market"

    if 'error' in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Trailing Stop order created! ({order_type})\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>trailing_distance</code>: {trailing_distance}%\n"
        f"<code>id</code>: {order['id']}"
    )


# Order management commands
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, command: CommandObject):
    """Cancel an order
    Usage: /cancel <symbol> <order_id>
    """
    args = command.args.strip().split() if command.args else ""

    if len(args) != 2:
        await message.answer("⚠️ Usage: /cancel <symbol> <order_id>")
        return

    symbol, order_id = args[0].upper(), args[1]
    service = OrderService()
    result = service.cancel_order(symbol, order_id)

    if 'error' in result:
        await message.answer(f"❌ Error: {result['error']}")
        return

    await message.answer(f"✅ Order {order_id} cancelled for {symbol}")


@router.message(Command("orders"))
async def cmd_open_orders(message: Message):
    """Show all open orders"""
    service = OrderService()
    orders = service.get_open_orders()

    if not orders:
        await message.answer("⚠️ No open orders")
        return

    msg = "📋 Open orders:\n\n"
    for order in orders:
        msg += (
            f"<b>{order['symbol']}</b> {order['side'].upper()}\n"
            f"  Type: {order['order_type']}\n"
            f"  Status: {order['status']}\n"
            f"  Amount: {order['amount']}\n"
            f"  Filled: {order['filled']}\n"
            f"  Price: {order['price']}\n"
            f"  ID: {order['id']}\n\n"
        )

    await message.answer(msg)
