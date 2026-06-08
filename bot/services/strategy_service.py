"""Strategy service for executing trades based on local strategy configuration"""

import logging
from typing import Any, Dict, Optional

import ccxt

from config import settings
from config.strategy import StrategyConfig, get_strategy_config

logger = logging.getLogger(__name__)


class StrategyService:
    """Service for executing trades using local strategy configuration"""

    def __init__(self):
        self.exchange = ccxt.bybit(
            {
                "apiKey": settings.bybit_api_key or "",
                "secret": settings.bybit_secret_key or "",
                "sandbox": settings.bybit_testnet,
            }
        )
        self.exchange.load_markets()

    def _calculate_position_size(
        self, risk: float, entry_price: float, leverage: int, balance: float
    ) -> float:
        """Calculate position size based on risk, leverage and entry price"""
        risk_amount = balance * risk

        position_size = risk_amount / entry_price

        return position_size

    def _get_balance_usdt(self) -> float:
        """Get USDT balance"""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get("USDT", {}).get("free", 0))
        except Exception:
            return 0.0

    def open_position_with_orders(
        self,
        symbol: str,
        side: str,  # 'long' or 'short'
        strategy_config: Optional[StrategyConfig] = None,
    ) -> Dict[str, Any]:
        """Open a position with TP/SL orders based on strategy config"""
        try:
            # Get strategy config for symbol
            if strategy_config is None:
                strategy_config = get_strategy_config(symbol)

            # Get current price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = float(ticker.get("last", 0))

            if current_price == 0:
                return {"error": "Cannot get current price"}

            # Set direction
            is_long = side.lower() in ["long", "buy"]
            entry_side = "buy" if is_long else "sell"
            close_side = (
                "sell" if is_long else "buy"
            )  # Side to close position (for TP/SL)

            # Get balance
            balance = float(self._get_balance_usdt())
            if balance <= 0:
                return {"error": "Insufficient balance"}

            # Calculate entry price (use current price for market entry)
            entry_price = current_price

            # Calculate stop price
            sl_percent = strategy_config.sl_percent
            if is_long:
                stop_price = entry_price * (1 - sl_percent)
                sl_trigger_direction = (
                    "descending"  # Price needs to go DOWN to trigger SL for long
                )
            else:
                stop_price = entry_price * (1 + sl_percent)
                sl_trigger_direction = (
                    "ascending"  # Price needs to go UP to trigger SL for short
                )

            # Calculate position size
            leverage = strategy_config.leverage
            position_size = self._calculate_position_size(
                risk=strategy_config.risk,
                entry_price=entry_price,
                leverage=leverage,
                balance=balance,
            )

            # Set position leverage
            try:
                self.exchange.set_leverage(leverage, symbol)
            except Exception:
                pass  # Leverage may already be set

            # Step 1: Open position with market order
            order_params = {"reduceOnly": False}

            try:
                market_order = self.exchange.create_market_order(
                    symbol, entry_side, position_size, None, order_params
                )
                logger.info(
                    f"Position opened: {side} {position_size} {symbol} at {entry_price}"
                )
            except Exception as e:
                return {"error": f"Market order failed: {e}"}

            # Wait for order to process
            import time

            time.sleep(1)

            # Step 2: Create ONLY Stop Loss order (one SL for whole position)
            sl_order = None
            sl_error = None

            if not strategy_config.trailing_stop:
                try:
                    sl_order = self.exchange.create_stop_market_order(
                        symbol,
                        close_side,  # Opposite direction to close position
                        position_size,  # Full position size
                        stop_price,
                        params={
                            "stopPrice": stop_price,
                            "triggerBy": "LastPrice",
                            "triggerDirection": sl_trigger_direction,  # REQUIRED by Bybit
                            "reduceOnly": True,  # Only reduce position
                        },
                    )
                    logger.info(f"Stop loss created at {stop_price} for {symbol}")
                except Exception as e:
                    sl_error = f"SL order failed: {e}"
                    logger.error(sl_error)
            else:
                sl_error = "Trailing stop not yet implemented"

            # Step 3: Create Take Profit orders (multiple levels, partial closes)
            tp_results = []

            if strategy_config.tp_count > 0:
                # Calculate amount for each TP level
                tp_amount = position_size / strategy_config.tp_count
                cumulative_amount = 0

                for i in range(strategy_config.tp_count):
                    tp_percent = strategy_config.tp_percent

                    # Calculate TP price and trigger direction for this level
                    if is_long:
                        tp_price = entry_price * (
                            1 + tp_percent * (i + 1) / strategy_config.tp_count
                        )
                        tp_trigger_direction = (
                            "ascending"  # Price needs to go UP to trigger TP for long
                        )
                        # Validate TP price is above entry price
                        if tp_price <= entry_price:
                            tp_results.append(
                                {
                                    "level": i + 1,
                                    "price": tp_price,
                                    "error": f"TP price {tp_price} must be above entry price {entry_price}",
                                }
                            )
                            continue
                    else:
                        tp_price = entry_price * (
                            1 - tp_percent * (i + 1) / strategy_config.tp_count
                        )
                        tp_trigger_direction = "descending"  # Price needs to go DOWN to trigger TP for short
                        # Validate TP price is below entry price
                        if tp_price >= entry_price:
                            tp_results.append(
                                {
                                    "level": i + 1,
                                    "price": tp_price,
                                    "error": f"TP price {tp_price} must be below entry price {entry_price}",
                                }
                            )
                            continue

                    # Initialize variable with default value
                    current_tp_amount = tp_amount

                    try:
                        # For last TP level, use remaining position size to avoid rounding issues
                        if i == strategy_config.tp_count - 1:
                            current_tp_amount = position_size - cumulative_amount
                            # Ensure we don't have negative or zero amount due to rounding
                            if current_tp_amount <= 0:
                                current_tp_amount = tp_amount

                        # Create TP order using create_order
                        tp_order = self.exchange.create_order(
                            symbol=symbol,
                            type="limit",
                            side=close_side,
                            amount=current_tp_amount,
                            price=tp_price,
                            params={
                                "reduceOnly": True,
                                "triggerPrice": tp_price,
                                "triggerBy": "LastPrice",
                                "triggerDirection": tp_trigger_direction,  # REQUIRED by Bybit
                                "timeInForce": "GTC",  # Good 'til cancelled
                            },
                        )

                        tp_results.append(
                            {
                                "level": i + 1,
                                "price": tp_price,
                                "amount": current_tp_amount,
                                "cumulative_percent": (
                                    (i + 1) / strategy_config.tp_count
                                )
                                * 100,
                                "order_id": tp_order.get("id", "unknown"),
                                "trigger_direction": tp_trigger_direction,
                                "success": True,
                            }
                        )

                        cumulative_amount += current_tp_amount
                        logger.info(
                            f"TP level {i + 1} created at {tp_price} (trigger: {tp_trigger_direction}) for {current_tp_amount} {symbol}"
                        )

                    except Exception as e:
                        tp_results.append(
                            {
                                "level": i + 1,
                                "price": tp_price,
                                "amount": current_tp_amount,
                                "error": f"TP order failed: {e}",
                                "success": False,
                            }
                        )
                        logger.error(f"TP level {i + 1} failed: {e}")

            return {
                "success": True,
                "market_order": market_order,
                "entry_price": entry_price,
                "position_size": position_size,
                "leverage": leverage,
                "sl_order": {
                    "success": sl_error is None,
                    "order": sl_order,
                    "error": sl_error,
                    "stop_price": stop_price,
                    "trigger_direction": sl_trigger_direction
                    if not strategy_config.trailing_stop
                    else None,
                },
                "tp_orders": tp_results,
                "tp_config": {
                    "count": strategy_config.tp_count,
                    "total_percent": strategy_config.tp_percent,
                    "amount_per_level": position_size / strategy_config.tp_count
                    if strategy_config.tp_count > 0
                    else 0,
                },
            }

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)
            return {"error": str(e)}

    def set_position_sl(
        self, symbol: str, sl_percent: float, use_trailing: bool = False
    ) -> Dict[str, Any]:
        """Set stop loss for an existing position"""
        try:
            # Get position
            positions = self.exchange.fetch_positions([symbol])
            if not positions:
                return {"error": f"No position for {symbol}"}

            position = positions[0]
            entry_price = float(position.get("entryPrice", 0))
            side = position.get("side", "").lower()

            if side not in ["long", "short"]:
                return {"error": "Invalid position side"}

            # Calculate stop price
            if use_trailing:
                # For trailing stop, we need to use Bybit's trailing stop API
                # This is platform-specific and may vary
                return {"error": "Trailing stop not yet implemented"}
            else:
                if side == "long":
                    stop_price = entry_price * (1 - sl_percent)
                else:
                    stop_price = entry_price * (1 + sl_percent)

                # Set stop loss using stop market order
                params = {
                    "stopPrice": stop_price,
                    "triggerBy": "LastPrice",
                    "reduceOnly": True,
                }

                # Get position size to close
                size = position.get("contracts", position.get("size", 0))

                order = self.exchange.create_stop_market_order(
                    symbol, "sell" if side == "long" else "buy", size, None, params
                )

                return {
                    "success": True,
                    "order": order,
                    "stop_price": stop_price,
                }

        except Exception as e:
            return {"error": str(e)}

    def get_symbols_config(self) -> Dict[str, Dict]:
        """Get all symbol configurations"""
        from config.strategy import strategy_config_store

        configs = strategy_config_store.get_all_configs()
        return {symbol: config.to_dict() for symbol, config in configs.items()}
