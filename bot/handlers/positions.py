from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.bybit_service import BybitService

router = Router()


class PositionState(StatesGroup):
    viewing = State()


def format_position(pos: dict) -> str:
    """Format position data for display"""
    symbol = pos.get('symbol', 'N/A')
    side = pos.get('side', 'N/A').upper()
    size = pos.get('size', 0)
    entry_price = pos.get('entry_price', 0)
    liq_price = pos.get('liq_price', 0)
    margin = pos.get('margin', 0)
    roe = pos.get('roee', 0)
    unrealized_pnl = pos.get('unrealized_pnl', 0)
    realized_pnl = pos.get('realized_pnl', 0)

    # Determine if long or short
    position_type = "LONG" if side == "BUY" else "SHORT"

    # Determine if profitable
    pnl_text = f"{unrealized_pnl:+.2f}"
    pnl_color = "🟢" if unrealized_pnl > 0 else ("🔴" if unrealized_pnl < 0 else "⚪")

    return (
        f"<b>{symbol}</b> {pnl_color} {pnl_text} USDT\n"
        f"  {position_type} | Size: {size:.4f}\n"
        f"  Entry: {entry_price:.2f} | Liq: {liq_price:.2f}\n"
        f"  Margin: {margin:.2f} USDT | ROE: {roe * 100:.2f}%\n"
        f"  Realized PnL: {realized_pnl:.2f} USDT"
    )


def create_position_keyboard(positions: list, current_page: int = 0, total_pages: int = 1) -> InlineKeyboardBuilder:
    """Create inline keyboard for position actions with pagination"""
    builder = InlineKeyboardBuilder()

    # Add position close buttons
    for pos in positions:
        symbol = pos.get('symbol', 'UNKNOWN')
        side = pos.get('side', 'N/A').upper()

        builder.button(
            text=f"❌ Close {symbol}",
            callback_data=f"close_pos:{symbol}:{side}"
        )

    # Pagination controls
    nav_row = []
    if current_page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"pos_page:{current_page - 1}"
            )
        )
    if current_page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Next",
                callback_data=f"pos_page:{current_page + 1}"
            )
        )

    if nav_row:
        builder.row(*nav_row)

    builder.button(
        text=f"✅ Close All",
        callback_data="close_all:all"
    )

    builder.adjust(1)
    return builder


def get_filtered_positions(positions: list, filter_arg: str) -> list:
    """Filter positions based on filter argument"""
    filtered_positions = []
    for pos in positions:
        side = pos.get('side', '').upper()
        unrealized_pnl = float(pos.get('unrealized_pnl', 0))

        if filter_arg == "long" and side != "BUY":
            continue
        if filter_arg == "short" and side != "SELL":
            continue
        if filter_arg == "profit" and unrealized_pnl <= 0:
            continue
        if filter_arg == "loss" and unrealized_pnl >= 0:
            continue
        if filter_arg and filter_arg.upper() in pos.get('symbol', ''):
            filtered_positions.append(pos)
            continue

        if not filter_arg or filter_arg in ["long", "short", "profit", "loss"]:
            filtered_positions.append(pos)

    return filtered_positions


async def send_positions_page(
    message_or_call,
    positions: list,
    page: int,
    filter_arg: str = "",
    is_callback: bool = False
):
    """Send a specific page of positions"""
    if not positions:
        if isinstance(message_or_call, Message):
            await message_or_call.answer("⚠️ There are no open positions")
        else:
            await message_or_call.answer("⚠️ There are no open positions", show_alert=True)
        return

    # Calculate pagination
    page_size = 5
    total_pages = (len(positions) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))  # Clamp page to valid range

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(positions))
    page_positions = positions[start_idx:end_idx]

    # Calculate totals for filtered positions
    total_size = sum(pos.get('size', 0) for pos in positions)
    total_unrealized_pnl = sum(float(pos.get('unrealized_pnl', 0)) for pos in positions)

    # Build message
    msg = f"<b>📊 Positions ({len(positions)}pcs, Total size: {total_size:.2f})</b>\n"
    msg += f"Unrealized PnL: {total_unrealized_pnl:+.2f} USDT\n"
    msg += f"Page {page + 1}/{total_pages}\n\n"

    for pos in page_positions:
        msg += format_position(pos) + "\n\n"

    # Create keyboard
    keyboard = create_position_keyboard(page_positions, page, total_pages)

    if is_callback:
        await message_or_call.message.edit_text(msg, reply_markup=keyboard.as_markup())
    else:
        await message_or_call.answer(msg, reply_markup=keyboard.as_markup())


@router.message(Command("positions"))
async def cmd_positions(message: Message, command: CommandObject, state: FSMContext):
    """Handle /positions command with optional filters

    Usage:
        /positions - show all positions
        /positions long - show only long positions
        /positions short - show only short positions
        /positions profit - show only profitable positions
        /positions loss - show only loss positions
        /positions <symbol> - show only for specific symbol
    """
    service = BybitService()
    positions = service.get_positions()

    # Get filter from command args
    filter_arg = command.args.strip().lower() if command.args else ""

    # Apply filters
    filtered_positions = get_filtered_positions(positions, filter_arg)

    if not filtered_positions:
        filter_name = {
            "long": "Longs",
            "short": "Shorts",
            "profit": "Profitable",
            "loss": "Loss positions",
        }.get(filter_arg, filter_arg)
        await message.answer(f"⚠️ No positions found for filter: {filter_name}")
        return

    # Save positions to state for callback handling
    await state.update_data(positions=filtered_positions, filter=filter_arg)

    await send_positions_page(message, filtered_positions, 0, filter_arg, False)


@router.callback_query(lambda call: call.data.startswith("pos_page:"))
async def callback_position_page(call: CallbackQuery, state: FSMContext):
    """Handle pagination callback"""
    data = await state.get_data()
    positions = data.get("positions", [])

    page = int(call.data.split(":")[1])
    filter_arg = data.get("filter", "")

    await send_positions_page(call, positions, page, filter_arg, True)


@router.callback_query(lambda call: call.data.startswith("close_pos:"))
async def callback_close_position(call: CallbackQuery, state: FSMContext):
    """Handle individual position close callback"""
    await call.answer("Processing...")

    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer("❌ Invalid request")
        return

    symbol = parts[1]
    side = parts[2]

    service = BybitService()
    result = service.close_position(symbol)

    if 'error' in result:
        await call.answer(f"❌ Error: {result['error']}")
    else:
        await call.answer(f"✅ Position {symbol} closed")


@router.callback_query(lambda call: call.data == "close_all:all")
async def callback_close_all(call: CallbackQuery, state: FSMContext):
    """Handle close all callback"""
    await call.answer("Processing...")

    data = await state.get_data()
    positions = data.get("positions", [])

    if not positions:
        await call.answer("⚠️ No positions to close")
        return

    service = BybitService()
    results = []

    for pos in positions:
        symbol = pos.get('symbol', '')
        result = service.close_position(symbol)
        if 'error' in result:
            results.append(f"❌ {symbol}: {result['error']}")
        else:
            results.append(f"✅ {symbol}: Closed")

    await call.message.edit_text("\n".join(results))
