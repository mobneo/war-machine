"""Strategy service for executing trades based on local strategy configuration"""
from typing import Optional, Dict, Any
from config import settings
from config.strategy import get_strategy_config, StrategyConfig
import ccxt


class StrategyService:
    """Service for executing trades using local strategy configuration"""

    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': settings.bybit_api_key or "",
            'secret': settings.bybit_secret_key or "",
        })
        self.exchange.load_markets()

    def _calculate_position_size(
        self,
        symbol: str,
        risk: float,
        entry_price: float,
        stop_price: float,
        leverage: int,
        balance: float
    ) -> float:
        """Calculate position size based on risk and stop distance"""
        # Risk amount in USDT
        risk_amount = balance * risk

        # Distance from entry to stop (in price units)
        stop_distance = abs(entry_price - stop_price)

        if stop_distance == 0:
            return 0

        # Position size = risk_amount / (stop_distance / entry_price * leverage)
        # This ensures we risk the specified percentage if stop is hit
        position_size = risk_amount / (stop_distance / entry_price * leverage)

        return position_size

    def _get_balance_usdt(self) -> float:
        """Get USDT balance"""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('USDT', {}).get('free', 0)
        except Exception:
            return 0

    def open_position_with_orders(
        self,
        symbol: str,
        side: str,  # 'long' or 'short'
        strategy_config: Optional[StrategyConfig] = None
    ) -> Dict[str, Any]:
        """Open a position with TP/SL orders based on strategy config"""
        try:
            # Get strategy config for symbol
            if strategy_config is None:
                strategy_config = get_strategy_config(symbol)

            # Get current price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker.get('last', 0)

            if current_price == 0:
                return {'error': 'Cannot get current price'}

            # Set direction
            is_long = side.lower() in ['long', 'buy']
            entry_side = 'buy' if is_long else 'sell'
            tp_side = 'sell' if is_long else 'buy'

            # Get balance
            balance = self._get_balance_usdt()
            if balance <= 0:
                return {'error': 'Insufficient balance'}

            # Calculate entry price (use current price for market entry)
            entry_price = current_price

            # Calculate stop price
            sl_percent = strategy_config.sl_percent
            if is_long:
                stop_price = entry_price * (1 - sl_percent)
            else:
                stop_price = entry_price * (1 + sl_percent)

            # Calculate position size
            leverage = strategy_config.leverage
            position_size = self._calculate_position_size(
                symbol=symbol,
                risk=strategy_config.risk,
                entry_price=entry_price,
                stop_price=stop_price,
                leverage=leverage,
                balance=balance
            )

            # Set position leverage
            try:
                self.exchange.set_leverage(leverage, symbol)
            except Exception as e:
                pass  # Leverage may already be set

            # Open position with market order
            order_params = {}
            if is_long:
                order_params['reduceOnly'] = False
            else:
                order_params['reduceOnly'] = False

            order = self.exchange.create_market_order(
                symbol, entry_side, position_size, None, order_params
            )

            if 'id' not in order:
                return {'error': f'Failed to open position: {order}'}

            # Wait a moment for position to be registered
            import time
            time.sleep(1)

            # Create TP orders
            tp_results = []
            tp_amount = position_size / strategy_config.tp_count

            for i in range(strategy_config.tp_count):
                tp_percent = strategy_config.tp_percent
                if is_long:
                    tp_price = entry_price * (1 + tp_percent * (i + 1) / strategy_config.tp_count)
                else:
                    tp_price = entry_price * (1 - tp_percent * (i + 1) / strategy_config.tp_count)

                tp_order = self.exchange.create_limit_order(
                    symbol, tp_side, tp_amount, tp_price
                )
                tp_results.append(tp_order)

            # Create SL order
            sl_results = {'order': None, 'error': None}
            if strategy_config.trailing_stop:
                # For trailing stop, we need to set it on the position
                # This is Bybit-specific - may need adjustment
                sl_results['error'] = 'Trailing stop not yet implemented'
            else:
                sl_order = self.exchange.create_stop_market_order(
                    symbol, tp_side, position_size, stop_price,
                    params={'stopPrice': stop_price, 'triggerBy': 'LastPrice'}
                )
                sl_results['order'] = sl_order

            return {
                'success': True,
                'position': order,
                'tp_orders': tp_results,
                'sl_order': sl_results,
                'entry_price': entry_price,
                'stop_price': stop_price,
                'position_size': position_size,
                'leverage': leverage,
            }

        except Exception as e:
            return {'error': str(e)}

    def set_position_sl(
        self,
        symbol: str,
        sl_percent: float,
        use_trailing: bool = False
    ) -> Dict[str, Any]:
        """Set stop loss for an existing position"""
        try:
            # Get position
            positions = self.exchange.fetch_positions([symbol])
            if not positions:
                return {'error': f'No position for {symbol}'}

            position = positions[0]
            entry_price = position.get('entryPrice', 0)
            side = position.get('side', '').lower()

            if side not in ['long', 'short']:
                return {'error': 'Invalid position side'}

            # Calculate stop price
            if use_trailing:
                # For trailing stop, we need to use Bybit's trailing stop API
                # This is platform-specific and may vary
                return {'error': 'Trailing stop not yet implemented'}
            else:
                if side == 'long':
                    stop_price = entry_price * (1 - sl_percent)
                else:
                    stop_price = entry_price * (1 + sl_percent)

                # Set stop loss using stop market order
                params = {
                    'stopPrice': stop_price,
                    'triggerBy': 'LastPrice',
                    'reduceOnly': True,
                }

                # Get position size to close
                size = position.get('contracts', position.get('size', 0))

                order = self.exchange.create_stop_market_order(
                    symbol, 'sell' if side == 'long' else 'buy',
                    size, None, params
                )

                return {
                    'success': True,
                    'order': order,
                    'stop_price': stop_price,
                }

        except Exception as e:
            return {'error': str(e)}

    def get_symbols_config(self) -> Dict[str, Dict]:
        """Get all symbol configurations"""
        from config.strategy import strategy_config_store
        configs = strategy_config_store.get_all_configs()
        return {symbol: config.to_dict() for symbol, config in configs.items()}
