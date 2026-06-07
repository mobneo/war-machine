import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services.bybit_service import BybitService
from config.strategy import strategy_config_store

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("config"))
async def cmd_config(message: Message):
    """Handle /config command - show balance, PnL, ROE, and local strategy config"""
    service = BybitService()

    # Get balance
    balance = service.get_balance("USDT")
    if "error" in balance:
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
        unrealized_pnl = float(
            pos.get(
                "unrealized_pnl", pos.get("unrealizedPnl", pos.get("unrealisedPnl", 0))
            )
            or 0
        )
        realized_pnl = float(
            pos.get(
                "realized_pnl", pos.get("realizedPnl", pos.get("cumRealisedPnl", 0))
            )
            or 0
        )
        size = float(pos.get("size", pos.get("contracts", 0)) or 0)
        roe = float(
            pos.get("roee", pos.get("realisedRoe", pos.get("realizedRoe", 0))) or 0
        )

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
        "👋 Hi! I'm a futures trading bot designed to execute trading strategies across various crypto exchanges.\n\n"
        "Available commands:\n"
        "/balance - show balance\n"
        "/config - show balance, PnL & ROE\n"
        "/positions - open positions\n"
        # "/positions long - show only long positions\n"
        # "/positions short - show only short positions\n"
        # "/positions profit - show only profitable positions\n"
        # "/positions loss - show only loss positions\n"
        "/close - close positions\n"
        # "/close long - close all long positions\n"
        # "/close short - close all short positions\n"
        # "/close profit - close all profitable positions\n"
        # "/close loss - close all loss positions\n"
        # "/close 'symbol' - close specific position\n"
        "/ticker &lt;symbol&gt; - asset price (e.g., /ticker BTCUSDT)\n"
        "/buy &lt;symbol&gt; &lt;amount&gt; - buy (for example, /buy BTCUSDT 0.001)\n"
        "/sell &lt;symbol&gt; &lt;amount&gt; - sell (for example, /sell BTCUSDT 0.001)"
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Handle /balance command"""
    service = BybitService()
    balance = service.get_balance("USDT")

    if "error" in balance:
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

    if "error" in ticker:
        await message.answer(f"❌ Error: {ticker['error']}")
        return

    info = ticker.get("info") or {}

    price_change_24h = info.get("price24hPcnt")
    try:
        change_pct = (
            f"{float(price_change_24h) * 100:+.2f}%"
            if price_change_24h is not None
            else "N/A"
        )
    except (ValueError, TypeError):
        change_pct = "N/A"

    funding_rate = info.get("fundingRate")
    try:
        funding_pct = (
            f"{float(funding_rate) * 100:.4f}%" if funding_rate is not None else "N/A"
        )
    except (ValueError, TypeError):
        funding_pct = "N/A"

    next_funding = info.get("nextFundingTime", "N/A")

    lines = [
        f"<b>📊 {symbol}</b>",
        "",
        f"<b>Price:</b>  <code>{ticker.get('last', 'N/A')}</code>",
    ]

    mark = ticker.get("markPrice") or info.get("markPrice")
    index = ticker.get("indexPrice") or info.get("indexPrice")
    if mark:
        lines.append(
            f"Mark: <code>{mark}</code>  |  Index: <code>{index or 'N/A'}</code>"
        )

    bid = ticker.get("bid")
    ask = ticker.get("ask")
    if bid and ask:
        lines.append(f"Bid: <code>{bid}</code>  |  Ask: <code>{ask}</code>")
        bid_vol = ticker.get("bidVolume") or info.get("bid1Size")
        ask_vol = ticker.get("askVolume") or info.get("ask1Size")
        if bid_vol or ask_vol:
            lines.append(
                f"Bid vol: <code>{bid_vol or '—'}</code>  |  Ask vol: <code>{ask_vol or '—'}</code>"
            )

    high_24 = info.get("highPrice24h") or ticker.get("high")
    low_24 = info.get("lowPrice24h") or ticker.get("low")
    if high_24 or low_24:
        lines.append(
            f"24h High: <code>{high_24 or '—'}</code>  |  Low: <code>{low_24 or '—'}</code>"
        )

    lines.append(f"24h Change: <code>{change_pct}</code>")

    turnover = info.get("turnover24h") or ticker.get("quoteVolume")
    volume = info.get("volume24h") or ticker.get("baseVolume")
    if turnover or volume:
        lines.append(
            f"Turnover: <code>{turnover or '—'}</code>  |  Vol: <code>{volume or '—'}</code>"
        )

    oi = info.get("openInterest")
    oi_val = info.get("openInterestValue")
    if oi:
        lines.append(
            f"OI: <code>{oi}</code>"
            + (f"  |  OI Val: <code>{oi_val}</code>" if oi_val else "")
        )

    lines.append(
        f"Funding: <code>{funding_pct}</code>  |  Next: <code>{next_funding}</code>"
    )

    await message.answer("\n".join(lines), parse_mode="HTML")


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

    if "error" in order:
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

    if "error" in order:
        await message.answer(f"❌ Error: {order['error']}")
        return

    await message.answer(
        f"✅ Sell order created!\n"
        f"<code>symbol</code>: {order['symbol']}\n"
        f"<code>amount</code>: {order['amount']}\n"
        f"<code>price</code>: {order['price']}\n"
        f"<code>id</code>: {order['id']}"
    )
