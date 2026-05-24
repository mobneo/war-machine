import ccxt
from typing import Optional, Dict, Any
from config import settings


class BybitService:
    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': settings.bybit_api_key or "",
            'secret': settings.bybit_secret_key or "",
        })
        # Load markets to validate connection
        self.exchange.load_markets()

    def get_balance(self, asset: str = "USDT") -> Dict[str, Any]:
        """Get wallet balance for specified asset"""
        try:
            balance = self.exchange.fetch_balance()
            free = balance.get(asset, {}).get('free', 0)
            used = balance.get(asset, {}).get('used', 0)
            total = balance.get(asset, {}).get('total', 0)
            return {
                'free': free,
                'used': used,
                'total': total,
            }
        except Exception as e:
            return {'error': str(e)}

    def get_positions(self, symbol: Optional[str] = None) -> list:
        """Get open futures positions. If symbol provided, return only that position"""
        try:
            # For futures, we need to use position info endpoint
            # Bybit v5 API uses different endpoint for positions
            if hasattr(self.exchange, 'fetch_positions'):
                positions = self.exchange.fetch_positions([symbol] if symbol else None)
                return [self._parse_position(pos) for pos in positions]

            # Fallback for older CCXT versions - parse from balance info
            balance = self.exchange.fetch_balance()
            result = []
            info = balance.get('info', {})

            # Handle Bybit response format for futures positions
            if isinstance(info, dict):
                result_list = info.get('result', {})
                if isinstance(result_list, dict):
                    positions_list = result_list.get('list', [])
                    if positions_list:
                        if isinstance(positions_list, list):
                            for pos in positions_list:
                                result.append(self._parse_position(pos))
                        elif isinstance(positions_list, dict):
                            result.append(self._parse_position(positions_list))

            return result
        except Exception:
            return []

    def _parse_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Parse position data to common format"""
        try:
            # Get raw size/contracts first (not float-converted yet)
            size = position.get('size', position.get('positionQty', position.get('contracts', 0)))

            # Get entry price - try multiple field names
            entry_price = position.get('entryPrice', position.get('avgPrice', position.get('averagePrice', 0)))

            return {
                'symbol': position.get('symbol', position.get('symbolName')),
                'side': position.get('side', position.get('positionSide')),
                'size': float(size) if size else 0.0,
                'entry_price': float(entry_price) if entry_price else 0.0,
                'liq_price': float(position.get('liqPrice', position.get('liqPrice', 0))),
                'margin': float(position.get('positionValue', position.get('positionMargin', position.get('notional', 0)))),
                'roee': float(position.get('realisedRoe', position.get('roee', position.get('realizedRoe', 0)))),
                # Add more fields for PnL calculation
                'unrealized_pnl': float(position.get('unrealizedPnl', position.get('unrealisedPnl', 0))),
                'realized_pnl': float(position.get('realizedPnl', position.get('cumRealisedPnl', 0))),
                'contracts': float(position.get('contracts', position.get('size', 0))),
            }
        except Exception:
            return position

    def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """Create a market order for futures trading"""
        try:
            # For futures, specify order type as Market
            order = self.exchange.create_market_order(symbol, side.lower(), amount)
            return {
                'id': order.get('id'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'amount': order.get('amount'),
                'price': order.get('price'),
                'status': order.get('status'),
            }
        except Exception as e:
            return {'error': str(e)}

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker (price) for a symbol"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': ticker.get('symbol'),
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'volume': ticker.get('volume'),
            }
        except Exception as e:
            return None

    def get_symbols(self) -> list:
        """Get list of available futures trading symbols"""
        # Filter for futures symbols (typically containing 'USDT' or similar)
        all_symbols = list(self.exchange.markets.keys())
        futures_symbols = [s for s in all_symbols if 'USDT' in s or 'USDC' in s]
        return futures_symbols

    def close_position(self, symbol: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Close a position for a symbol. If amount is provided, close partial position."""
        try:
            positions = self.get_positions(symbol)
            if not positions:
                return {'error': f'No open position for {symbol}'}

            position = positions[0]
            side = 'sell' if position['side'] == 'long' else 'buy'

            # If amount not specified, close full position
            close_amount = amount if amount is not None else position['size']

            # Use reduce_only to close position
            params = {'reduceOnly': True}
            order = self.exchange.create_market_order(
                symbol.upper(), side, close_amount, None, params
            )
            return self._parse_order_result(order)
        except Exception as e:
            return {'error': str(e)}

    def _parse_order_result(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order result to common format"""
        try:
            return {
                'id': order.get('id'),
                'client_order_id': order.get('clientOrderId'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'order_type': order.get('type'),
                'status': order.get('status'),
                'amount': order.get('amount'),
                'filled': order.get('filled', 0),
                'remaining': order.get('remaining', order.get('amount')),
                'price': order.get('price'),
                'stop_price': order.get('stopPrice'),
                'trigger_price': order.get('triggerPrice'),
                'trailing_price': order.get('trailingPrice'),
                'reduce_only': order.get('reduceOnly', False),
                'created_at': order.get('timestamp'),
            }
        except Exception:
            return order

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return [self._parse_order_result(o) for o in orders]
        except Exception as e:
            return []

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order by order_id"""
        try:
            order = self.exchange.cancel_order(order_id, symbol.upper())
            return self._parse_order_result(order)
        except Exception as e:
            return {'error': str(e)}

    def cancel_orders_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """Cancel all orders for a symbol"""
        try:
            self.exchange.cancel_all_orders(symbol.upper())
            return {'success': True, 'message': f'All orders for {symbol} cancelled'}
        except Exception as e:
            return {'error': str(e)}

    def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all open orders"""
        try:
            orders = self.exchange.fetch_open_orders()
            for order in orders:
                try:
                    self.exchange.cancel_order(order.get('id'), order.get('symbol'))
                except Exception:
                    pass
            return {'success': True, 'message': 'All orders cancelled'}
        except Exception as e:
            return {'error': str(e)}

    def cancel_inactive_orders(self) -> Dict[str, Any]:
        """Cancel orders that are not related to active positions"""
        try:
            # Get active positions to know which symbols are in use
            positions = self.get_positions()
            active_symbols = {pos.get('symbol') for pos in positions}

            # Get all open orders
            orders = self.exchange.fetch_open_orders()
            cancelled_count = 0

            for order in orders:
                symbol = order.get('symbol')
                # Cancel orders for symbols not in active positions
                if symbol and symbol not in active_symbols:
                    try:
                        self.exchange.cancel_order(order.get('id'), symbol)
                        cancelled_count += 1
                    except Exception:
                        pass

            return {'success': True, 'cancelled_count': cancelled_count}
        except Exception as e:
            return {'error': str(e)}
