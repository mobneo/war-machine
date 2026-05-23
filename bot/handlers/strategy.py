from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.strategy import (
    get_strategy_config,
    strategy_config_store,
    StrategyConfig
)
from bot.services.strategy_service import StrategyService

router = Router()


class StrategyState(StatesGroup):
    setting_risk = State()
    setting_tp = State()
    setting_sl = State()
    setting_leverage = State()


def format_strategy_config(symbol: str, config: StrategyConfig) -> str:
    """Format strategy configuration for display"""
    risk_percent = config.risk * 100
    tp_percent = config.tp_percent * 100
    sl_percent = config.sl_percent * 100

    msg = f"<b>⚙️ Strategy: {symbol}</b>\n\n"
    msg += f"  Risk: {risk_percent:.1f}%\n"
    msg += f"  TP: {tp_percent:.1f}% (x{config.tp_count})\n"
    if config.trailing_stop:
        msg += "  SL: Trailing Stop\n"
    else:
        msg += f"  SL: {sl_percent:.1f}% (Stop Loss)\n"
    msg += f"  Leverage: {config.leverage}x"

    return msg


def create_strategy_keyboard(symbol: str) -> InlineKeyboardBuilder:
    """Create inline keyboard for strategy settings"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="💰 Risk",
        callback_data=f"strategy:risk:{symbol}"
    )
    builder.button(
        text="🎯 TP",
        callback_data=f"strategy:tp:{symbol}"
    )
    builder.button(
        text="🛑 SL",
        callback_data=f"strategy:sl:{symbol}"
    )
    builder.button(
        text="📈 Leverage",
        callback_data=f"strategy:leverage:{symbol}"
    )

    builder.button(
        text="🔄 Reset",
        callback_data=f"strategy:reset:{symbol}"
    )
    builder.button(
        text="⬅️ Back",
        callback_data="strategy:menu"
    )

    builder.adjust(2)
    return builder


@router.message(Command("strategy"))
async def cmd_strategy(message: Message, command: CommandObject, state: FSMContext):
    """Handle /strategy command - manage local strategy configuration

    Usage:
        /strategy - show menu
        /strategy <symbol> - show config for symbol
        /strategy <symbol> <risk> <tp> <sl> <leverage> - set all at once
    """
    args = command.args.strip().split() if command.args else []

    if not args:
        # Show list of configured symbols
        configs = strategy_config_store.get_all_configs()
        if not configs:
            await message.answer(
                "⚠️ No strategy configurations yet.\n"
                "Use /strategy <symbol> to create one."
            )
            return

        msg = "<b>📋 Strategy Configurations</b>\n\n"
        for symbol, config in configs.items():
            msg += f"<code>{symbol}</code>:\n"
            msg += f"  Risk: {config.risk * 100:.1f}% | TP: {config.tp_percent * 100:.1f}%\n"
            msg += f"  SL: {config.sl_percent * 100:.1f}% | Leverage: {config.leverage}x\n\n"

        await message.answer(msg)
        return

    symbol = args[0].upper()

    if len(args) == 1:
        # Show config for symbol
        config = get_strategy_config(symbol)
        await message.answer(
            format_strategy_config(symbol, config),
            reply_markup=create_strategy_keyboard(symbol).as_markup()
        )
        return

    # Set configuration from args
    if len(args) >= 5:
        try:
            risk = float(args[1])
            tp = float(args[2])
            sl = float(args[3])
            leverage = int(args[4])

            config = strategy_config_store.update_risk(symbol, risk)
            config = strategy_config_store.update_tp(symbol, tp, config.tp_count)
            config = strategy_config_store.update_sl(symbol, sl, config.trailing_stop)
            config = strategy_config_store.update_leverage(symbol, leverage)

            await message.answer(
                f"✅ Strategy configured for {symbol}:\n"
                f"  Risk: {risk * 100:.1f}%\n"
                f"  TP: {tp * 100:.1f}%\n"
                f"  SL: {sl * 100:.1f}%\n"
                f"  Leverage: {leverage}x",
                reply_markup=create_strategy_keyboard(symbol).as_markup()
            )
        except ValueError:
            await message.answer("❌ Invalid values. Usage: /strategy <symbol> <risk> <tp> <sl> <leverage>")
        return

    await message.answer("⚠️ Usage: /strategy <symbol> [risk tp sl leverage]")


@router.callback_query(lambda call: call.data.startswith("strategy:"))
async def callback_strategy(call: CallbackQuery, state: FSMContext):
    """Handle strategy callback actions"""
    data = call.data.split(":")
    if len(data) < 3:
        await call.answer("❌ Invalid request")
        return

    action = data[1]
    symbol = data[2]

    if action == "menu":
        await call.message.edit_text("⚙️ Strategy settings menu")
        return

    if action == "reset":
        strategy_config_store.delete_config(symbol)
        await call.answer(f"✅ Configuration reset for {symbol}")
        await call.message.edit_text(
            f"⚠️ No configuration for {symbol}. Use /strategy to set one.",
            reply_markup=None
        )
        return

    # Show input prompt
    await state.update_data(current_symbol=symbol, current_action=action)
    await call.answer(f"⚙️ {action.capitalize()} settings for {symbol}")

    messages = {
        "risk": "Enter risk percentage (0-100, e.g., 1 for 1%):",
        "tp": "Enter TP percentage (e.g., 2 for 2%):",
        "sl": "Enter SL percentage (e.g., 1 for 1%):",
        "leverage": "Enter leverage (1-100):",
    }

    await call.message.answer(messages.get(action, "Enter value:"))


@router.message(StrategyState.setting_risk)
async def set_risk(message: Message, state: FSMContext):
    """Handle risk setting"""
    await _handle_float_setting(message, state, "risk", 0, 100, lambda v: v / 100)


@router.message(StrategyState.setting_tp)
async def set_tp(message: Message, state: FSMContext):
    """Handle TP setting"""
    await _handle_float_setting(message, state, "tp", 0.1, 1000, lambda v: v / 100)


@router.message(StrategyState.setting_sl)
async def set_sl(message: Message, state: FSMContext):
    """Handle SL setting"""
    await _handle_float_setting(message, state, "sl", 0.1, 100, lambda v: v / 100)


@router.message(StrategyState.setting_leverage)
async def set_leverage(message: Message, state: FSMContext):
    """Handle leverage setting"""
    await _handle_int_setting(message, state, "leverage", 1, 100)


async def _handle_float_setting(
    message: Message,
    state: FSMContext,
    setting_name: str,
    min_val: float,
    max_val: float,
    transform
):
    """Generic handler for float settings"""
    try:
        value = float(message.text)
        transformed = transform(value)

        if not (min_val <= transformed <= max_val):
            await message.answer(f"❌ Value must be between {min_val} and {max_val}")
            return

        data = await state.get_data()
        symbol = data.get("current_symbol")
        action = data.get("current_action")

        if not symbol:
            await message.answer("❌ No symbol selected")
            await state.clear()
            return

        config = get_strategy_config(symbol)

        if action == "risk":
            strategy_config_store.update_risk(symbol, transformed)
        elif action == "tp":
            strategy_config_store.update_tp(symbol, transformed, config.tp_count)
        elif action == "sl":
            strategy_config_store.update_sl(symbol, transformed, config.trailing_stop)

        await message.answer(f"✅ {setting_name.capitalize()} set to {value}")
        await state.clear()

        # Show updated config
        config = get_strategy_config(symbol)
        await message.answer(
            format_strategy_config(symbol, config),
            reply_markup=create_strategy_keyboard(symbol).as_markup()
        )

    except ValueError:
        await message.answer("❌ Invalid number. Try again:")


async def _handle_int_setting(
    message: Message,
    state: FSMContext,
    setting_name: str,
    min_val: int,
    max_val: int
):
    """Generic handler for int settings"""
    try:
        value = int(message.text)

        if not (min_val <= value <= max_val):
            await message.answer(f"❌ Value must be between {min_val} and {max_val}")
            return

        data = await state.get_data()
        symbol = data.get("current_symbol")
        action = data.get("current_action")

        if not symbol:
            await message.answer("❌ No symbol selected")
            await state.clear()
            return

        if action == "leverage":
            strategy_config_store.update_leverage(symbol, value)

        await message.answer(f"✅ {setting_name.capitalize()} set to {value}")
        await state.clear()

        # Show updated config
        config = get_strategy_config(symbol)
        await message.answer(
            format_strategy_config(symbol, config),
            reply_markup=create_strategy_keyboard(symbol).as_markup()
        )

    except ValueError:
        await message.answer("❌ Invalid number. Try again:")


@router.message(Command("trading"))
async def cmd_trading(message: Message, command: CommandObject, state: FSMContext):
    """Handle /trading command - open position based on local strategy

    Usage:
        /trading <symbol> <side> - open position (side: long/short)
    """
    args = command.args.strip().split() if command.args else []

    if len(args) != 2:
        await message.answer("⚠️ Usage: /trading <symbol> <side>\nSide: long or short")
        return

    symbol = args[0].upper()
    side = args[1].lower()

    if side not in ["long", "short"]:
        await message.answer("❌ Side must be 'long' or 'short'")
        return

    # Get strategy config
    config = get_strategy_config(symbol)

    service = StrategyService()
    result = service.open_position_with_orders(symbol, side, config)

    if 'error' in result:
        await message.answer(f"❌ Error: {result['error']}")
        return

    # Format and send result
    entry_price = result.get('entry_price', 0)
    position_size = result.get('position_size', 0)
    leverage = result.get('leverage', 0)

    msg = "<b>🚀 Position opened!</b>\n\n"
    msg += f"<code>{symbol}</code> <b>{side.upper()}</b>\n"
    msg += f"  Entry: {entry_price:.2f}\n"
    msg += f"  Size: {position_size:.4f}\n"
    msg += f"  Leverage: {leverage}x\n\n"

    # TP/SL info
    tp_percent = config.tp_percent * 100
    sl_percent = config.sl_percent * 100
    msg += f"  TP: {tp_percent:.1f}% | SL: {sl_percent:.1f}%\n"

    await message.answer(msg)

    # Show details of TP/SL orders
    tp_orders = result.get('tp_orders', [])
    if tp_orders:
        msg = "<b>✅ Take Profit orders created:</b>\n"
        for i, tp in enumerate(tp_orders):
            msg += f"  TP {i + 1}: {tp}\n"
        await message.answer(msg)
