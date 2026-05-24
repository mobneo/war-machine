from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

from bot.services.bybit_service import BybitService
from config.strategy import strategy_config_store

router = Router()


@router.message(Command("config"))
async def cmd_config(message: Message):
    """Handle /config command - show balance, PnL, ROE, and local strategy config"""
    service = BybitService()

    # Get balance
    balance = service.get_balance("USDT")
    if 'error' in balance:
        await message.answer(f"❌ Error fetching balance: {balance['error']}")
        return

    # Get positions for PnL and ROE calculation
    positions = service.get_positions()

    # Calculate total PnL and ROE
    total_unrealized_pnl = 0.0
    total_realized_pnl = 0.0
    total_roe = 0.0
    total_size = 0.0
    position_count = len(positions)

    for pos in positions:
        # Get values from parsed position - try different field names
        unrealized_pnl = float(pos.get('unrealized_pnl', pos.get('unrealizedPnl', pos.get('unrealisedPnl', 0))) or 0)
        realized_pnl = float(pos.get('realized_pnl', pos.get('realizedPnl', pos.get('cumRealisedPnl', 0))) or 0)
        size = float(pos.get('size', pos.get('contracts', 0)) or 0)
        roe = float(pos.get('roee', pos.get('realisedRoe', pos.get('realizedRoe', 0))) or 0)

        total_unrealized_pnl += unrealized_pnl
        total_realized_pnl += realized_pnl
        total_size += size
        total_roe += roe

    avg_roe = total_roe / position_count if position_count > 0 else 0

    # Format balance
    balance_text = (
        f"💰 Balance USDT:\n"
        f"  available: {balance['free']:.2f}\n"
        f"  frozen: {balance['used']:.2f}\n"
        f"  total: {balance['total']:.2f}\n"
    )

    # Format positions info
    if position_count > 0:
        positions_text = (
            f"📊 Positions: {position_count} pcs. (Total size: {total_size:.2f})\n"
            f"  Unrealized PnL: {total_unrealized_pnl:.2f} USDT\n"
            f"  Realized PnL: {total_realized_pnl:.2f} USDT\n"
            f"  Average ROE: {avg_roe * 100:.2f}%"
        )
    else:
        positions_text = "📊 No open positions"

    # Format local strategy configs
    strategy_configs = strategy_config_store.get_all_configs()
    if strategy_configs:
        strategy_text = "\n⚙️ Local Strategy Configs:\n"
        for symbol, config in strategy_configs.items():
            risk_pct = config.risk * 100
            tp_pct = config.tp_percent * 100
            sl_pct = config.sl_percent * 100
            sl_type = "Trailing" if config.trailing_stop else "Stop Loss"
            strategy_text += (
                f"  {symbol}:\n"
                f"    Risk: {risk_pct:.1f}% | TP: {tp_pct:.1f}% (x{config.tp_count})\n"
                f"    SL: {sl_pct:.1f}% ({sl_type}) | Leverage: {config.leverage}x\n"
            )
    else:
        strategy_text = "\n⚙️ No local strategy configurations"

    await message.answer(
        f"<b>⚙️ Config / Account Info</b>\n\n"
        f"{balance_text}\n"
        f"{positions_text}\n"
        f"{strategy_text}"
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    await message.answer(
        "👋 Hi! I'm a futures trading bot for Bybit.\n\n"
        "Available commands:\n"
        "/balance - show balance\n"
        "/config - show balance, PnL & ROE\n"
        "/positions - open positions\n"
        "/positions long - show only long positions\n"
        "/positions short - show only short positions\n"
        "/positions profit - show only profitable positions\n"
        "/positions loss - show only loss positions\n"
        "/close all - close all positions\n"
        "/close long - close all long positions\n"
        "/close short - close all short positions\n"
        "/close profit - close all profitable positions\n"
        "/close loss - close all loss positions\n"
        "/close 'symbol' - close specific position\n"
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




@router.message(Command("ticker"))
async def cmd_ticker(message: Message, command: CommandObject):
    """Handle /ticker <symbol> command"""
    symbol = command.args.strip().upper() if command.args else None

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
        f" last: {ticker['last']}\n"
        f" bid: {ticker['bid']}\n"
        f" ask: {ticker['ask']}\n"
        f" volume: {ticker['volume']}"
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message, command: CommandObject):
    """Handle /buy <symbol> <amount> command"""
    args = command.args.strip().split() if command.args else ""

    if len(args) != 2:
        await message.answer("⚠️ Usage: /buy [symbol] [amount]")
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
async def cmd_sell(message: Message, command: CommandObject):
    """Handle /sell <symbol> <amount> command"""
    args = command.args.strip().split() if command.args else ""

    if len(args) != 2:
        await message.answer("⚠️ Usage: /sell [symbol] [amount]")
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
