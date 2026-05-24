from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("commands"))
async def cmd_commands(message: Message):
    """Handle /commands command - show all available commands"""
    await message.answer(
        "<b>📜 Available Commands</b>\n\n"

        "<b>Basic Commands:</b>\n"
        "/start - Greeting message\n"
        "/commands - Show all available commands\n"
        "/balance - Show USDT balance\n"
        "/config - Show balance, PnL & ROE\n"
        "/ticker <symbol> - Asset price (e.g., /ticker BTCUSDT)\n\n"

        "<b>Trading:</b>\n"
        "/buy <symbol> <amount> - Buy (e.g., /buy BTCUSDT 0.001)\n"
        "/sell <symbol> <amount> - Sell (e.g., /sell BTCUSDT 0.001)\n"
        "/trading <symbol> <side> - Open position based on strategy (long/short)\n\n"

        "<b>Positions:</b>\n"
        "/positions - Show all open positions\n"
        "/positions long - Show only long positions\n"
        "/positions short - Show only short positions\n"
        "/positions profit - Show only profitable positions\n"
        "/positions loss - Show only loss positions\n"
        "/positions <symbol> - Show positions for specific symbol\n\n"

        "<b>Close Positions:</b>\n"
        "/close all - Close all positions\n"
        "/close long - Close all long positions\n"
        "/close short - Close all short positions\n"
        "/close profit - Close all profitable positions\n"
        "/close loss - Close all loss positions\n"
        "/close <symbol> - Close specific position\n\n"

        "<b>Orders:</b>\n"
        "/orders - Show all orders\n"
        "/orders open - Show only open orders\n"
        "/orders filled - Show only filled orders\n"
        "/orders cancelled - Show only cancelled orders\n"
        "/orders active - Show orders for symbols with active positions\n"
        "/orders <symbol> - Show orders for specific symbol\n\n"

        "<b>Advanced Orders:</b>\n"
        "/sl <symbol> <amount> <stop_price> [limit_price] - Stop-loss order\n"
        "/tp <symbol> <amount> <trigger_price> [limit_price] - Take-profit order\n"
        "/trailing <symbol> <amount> <distance%> [limit_price] - Trailing-stop order\n"
        "/cancel <symbol> <order_id> - Cancel specific order\n\n"

        "<b>Strategy Configuration:</b>\n"
        "/strategy - Show strategy configurations\n"
        "/strategy <symbol> - Show config for symbol\n"
        "/strategy <symbol> <risk> <tp> <sl> <leverage> - Set configuration\n"
        "/global_strategy - Show/edit global strategy defaults\n\n"

        "<b>Order Management:</b>\n"
        "/cancel_symbol <symbol> - Cancel all orders for a symbol\n"
        "/cancel_inactive - Cancel orders for symbols without positions"
    )
