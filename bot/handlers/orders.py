from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.bybit_service import BybitService

router = Router()


class OrderState(StatesGroup):
    viewing = State()


def format_order(order: dict) -> str:
    """Format order data for display"""
    symbol = order.get('symbol', 'N/A')
    side = order.get('side', 'N/A').upper()
    order_type = order.get('order_type', 'N/A')
    status = order.get('status', 'N/A')
    amount = order.get('amount', 0)
    filled = order.get('filled', 0)
    price = order.get('price', 0)
    stop_price = order.get('stop_price', 0)
    order_id = order.get('id', 'N/A')

    # Determine if long or short
    order_side = "LONG" if side == "BUY" else "SHORT"

    # Status emoji
    status_emoji = {
        "Open": "🟢",
        "pending": "🟡",
        "new": "🟡",
        "filled": "✅",
        "cancelled": "❌",
        "canceled": "❌",
        "rejected": "🔴",
        "error": "🔴",
    }.get(status.lower(), "⚪")

    msg = f"<b>{symbol}</b> {status_emoji} {status.upper()}\n"
    msg += f"  {order_side} | {order_type.upper()}\n"
    msg += f"  Amount: {amount:.4f} | Filled: {filled:.4f}\n"
    msg += f"  Price: {price:.2f}"

    if stop_price:
        msg += f" | Stop: {stop_price:.2f}"

    msg += f"\n  ID: {order_id}"

    return msg


def create_order_keyboard(orders: list, current_page: int = 0, total_pages: int = 1) -> InlineKeyboardBuilder:
    """Create inline keyboard for order actions with pagination"""
    builder = InlineKeyboardBuilder()

    # Add order cancel buttons
    for order in orders:
        symbol = order.get('symbol', 'UNKNOWN')
        order_id = order.get('id', '')

        if order_id and order.get('status', '').lower() in ['open', 'pending', 'new']:
            builder.button(
                text=f"❌ Cancel {symbol}",
                callback_data=f"cancel_order:{symbol}:{order_id}"
            )

    # Pagination controls
    nav_row = []
    if current_page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"order_page:{current_page - 1}"
            )
        )
    if current_page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Next",
                callback_data=f"order_page:{current_page + 1}"
            )
        )

    if nav_row:
        builder.row(*nav_row)

    builder.button(
        text="❌ Cancel All",
        callback_data="cancel_all:all"
    )

    builder.adjust(1)
    return builder


def get_filtered_orders(orders: list, filter_arg: str) -> list:
    """Filter orders based on filter argument"""
    filtered_orders = []

    if not filter_arg or filter_arg.lower() in ['open', 'all']:
        return orders

    filter_lower = filter_arg.lower()

    for order in orders:
        status = order.get('status', '').lower()
        symbol = order.get('symbol', '')

        # Filter by status
        if filter_lower in ['open', 'pending', 'new']:
            if status == filter_lower or status == 'open':
                filtered_orders.append(order)
        elif filter_lower == 'filled':
            if status == 'filled':
                filtered_orders.append(order)
        elif filter_lower == 'cancelled':
            if status in ['cancelled', 'canceled']:
                filtered_orders.append(order)
        # Filter by symbol
        elif filter_lower in symbol.lower():
            filtered_orders.append(order)
        # Filter by active (open orders for symbols in positions)
        elif filter_lower == 'active':
            # Will be filtered by handler
            filtered_orders.append(order)

    return filtered_orders


async def send_orders_page(
    message_or_call,
    orders: list,
    page: int,
    filter_arg: str = "",
    is_callback: bool = False
):
    """Send a specific page of orders"""
    if not orders:
        if isinstance(message_or_call, Message):
            await message_or_call.answer("⚠️ There are no orders")
        else:
            await message_or_call.answer("⚠️ There are no orders", show_alert=True)
        return

    # Calculate pagination
    page_size = 5
    total_pages = (len(orders) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))  # Clamp page to valid range

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(orders))
    page_orders = orders[start_idx:end_idx]

    # Calculate totals for filtered orders
    total_amount = sum(order.get('amount', 0) for order in orders)
    total_filled = sum(order.get('filled', 0) for order in orders)

    # Build message
    msg = f"<b>📋 Orders ({len(orders)}pcs, Total: {total_amount:.2f})</b>\n"
    msg += f"Filled: {total_filled:.2f}\n"
    msg += f"Page {page + 1}/{total_pages}\n\n"

    for order in page_orders:
        msg += format_order(order) + "\n\n"

    # Create keyboard
    keyboard = create_order_keyboard(page_orders, page, total_pages)

    if is_callback:
        await message_or_call.message.edit_text(msg, reply_markup=keyboard.as_markup())
    else:
        await message_or_call.answer(msg, reply_markup=keyboard.as_markup())


@router.message(Command("orders"))
async def cmd_open_orders(message: Message, command: CommandObject, state: FSMContext):
    """Handle /orders command with optional filters

    Usage:
        /orders - show all orders
        /orders open - show only open orders
        /orders filled - show only filled orders
        /orders cancelled - show only cancelled orders
        /orders <symbol> - show only orders for specific symbol
        /orders active - show orders for symbols with active positions
    """
    service = BybitService()

    # Get all open orders first
    orders = service.get_open_orders()

    # Get filter from command args
    filter_arg = command.args.strip().lower() if command.args else ""

    # Apply filters
    filtered_orders = get_filtered_orders(orders, filter_arg)

    # Handle special "active" filter - show orders for symbols with active positions
    if filter_arg == "active":
        positions = service.get_positions()
        active_symbols = {pos.get('symbol') for pos in positions}
        filtered_orders = [o for o in orders if o.get('symbol') in active_symbols]

    if not filtered_orders:
        filter_name = filter_arg if filter_arg else "All"
        await message.answer(f"⚠️ No orders found for filter: {filter_name}")
        return

    # Save orders to state for callback handling
    await state.update_data(orders=filtered_orders, filter=filter_arg)

    await send_orders_page(message, filtered_orders, 0, filter_arg, False)


@router.callback_query(lambda call: call.data.startswith("order_page:"))
async def callback_order_page(call: CallbackQuery, state: FSMContext):
    """Handle pagination callback"""
    data = await state.get_data()
    orders = data.get("orders", [])

    page = int(call.data.split(":")[1])
    filter_arg = data.get("filter", "")

    await send_orders_page(call, orders, page, filter_arg, True)


@router.callback_query(lambda call: call.data.startswith("cancel_order:"))
async def callback_cancel_order(call: CallbackQuery, state: FSMContext):
    """Handle individual order cancel callback"""
    await call.answer("Processing...")

    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer("❌ Invalid request")
        return

    symbol = parts[1]
    order_id = parts[2]

    service = BybitService()
    result = service.cancel_order(symbol, order_id)

    if 'error' in result:
        await call.answer(f"❌ Error: {result['error']}")
    else:
        await call.answer(f"✅ Order {order_id} cancelled for {symbol}")


@router.callback_query(lambda call: call.data == "cancel_all:all")
async def callback_cancel_all(call: CallbackQuery, state: FSMContext):
    """Handle cancel all callback"""
    await call.answer("Processing...")

    data = await state.get_data()
    orders = data.get("orders", [])

    if not orders:
        await call.answer("⚠️ No orders to cancel")
        return

    service = BybitService()
    results = []

    for order in orders:
        symbol = order.get('symbol', '')
        order_id = order.get('id', '')
        if order_id:
            result = service.cancel_order(symbol, order_id)
            if 'error' in result:
                results.append(f"❌ {symbol} {order_id}: {result['error']}")
            else:
                results.append(f"✅ {symbol}: Cancelled")

    if results:
        await call.message.edit_text("\n".join(results))
    else:
        await call.message.edit_text("✅ All orders cancelled")


@router.message(Command("cancel_inactive"))
async def cmd_cancel_inactive(message: Message):
    """Cancel orders for symbols without active positions"""
    service = BybitService()
    result = service.cancel_inactive_orders()

    if 'error' in result:
        await message.answer(f"❌ Error: {result['error']}")
    else:
        await message.answer(
            f"✅ Cancelled {result.get('cancelled_count', 0)} inactive orders"
        )


@router.message(Command("cancel_symbol"))
async def cmd_cancel_symbol(message: Message, command: CommandObject):
    """Cancel all orders for a specific symbol
    Usage: /cancel_symbol <symbol>
    """
    args = command.args.strip() if command.args else ""

    if not args:
        await message.answer("⚠️ Usage: /cancel_symbol <symbol>")
        return

    symbol = args.upper()
    service = BybitService()
    result = service.cancel_orders_by_symbol(symbol)

    if 'error' in result:
        await message.answer(f"❌ Error: {result['error']}")
    else:
        await message.answer(f"✅ {result.get('message', 'Orders cancelled')}")
