from typing import Optional, Dict, Any
from config import settings
import ccxt


class OrderService:
    """Service for creating various order types: market, limit, stop-loss, take-profit, trailing-stop"""

    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': settings.bybit_api_key or "",
            'secret': settings.bybit_secret_key or "",
        })
        self.exchange.load_markets()

    def create_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """Create a market order"""
        try:
            order = self.exchange.create_market_order(symbol.upper(), side.lower(), amount)
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        """Create a limit order"""
        try:
            order = self.exchange.create_limit_order(symbol.upper(), side.lower(), amount, price)
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_stop_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Create a stop-market order (triggered when price reaches stop_price)"""
        try:
            params = {
                'stopPrice': stop_price,
                'triggerBy': 'LastPrice',
                'reduceOnly': reduce_only,
            }
            order = self.exchange.create_market_order(
                symbol.upper(), side.lower(), amount, None, params
            )
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_stop_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        stop_price: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Create a stop-limit order (limit order with stop trigger)"""
        try:
            params = {
                'stopPrice': stop_price,
                'triggerBy': 'LastPrice',
                'reduceOnly': reduce_only,
            }
            order = self.exchange.create_limit_order(
                symbol.upper(), side.lower(), amount, price, params
            )
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        trigger_price: float,
        order_type: str = "market",
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a take-profit order"""
        if order_type == "limit" and not price:
            return {'error': 'Price required for limit take-profit order'}

        try:
            params = {
                'takeProfit': trigger_price,
                'triggerBy': 'LastPrice',
            }
            if order_type == "market":
                order = self.exchange.create_market_order(
                    symbol.upper(), side.lower(), amount, None, params
                )
            else:
                order = self.exchange.create_limit_order(
                    symbol.upper(), side.lower(), amount, price, params
                )
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        order_type: str = "market",
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a stop-loss order"""
        if order_type == "limit" and not price:
            return {'error': 'Price required for limit stop-loss order'}

        try:
            params = {
                'stopLoss': stop_price,
                'triggerBy': 'LastPrice',
            }
            if order_type == "market":
                order = self.exchange.create_market_order(
                    symbol.upper(), side.lower(), amount, None, params
                )
            else:
                order = self.exchange.create_limit_order(
                    symbol.upper(), side.lower(), amount, price, params
                )
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        trailing_stop: float,
        order_type: str = "market",
        price: Optional[float] = None,
        reduce_only: bool = True
    ) -> Dict[str, Any]:
        """Create a trailing-stop order (trailing_stop in % from current price)"""
        if order_type == "limit" and not price:
            return {'error': 'Price required for limit trailing-stop order'}

        try:
            params = {
                'triggerBy': 'LastPrice',
                'triggerPrice': trailing_stop,
                'reduceOnly': reduce_only,
            }
            if order_type == "market":
                order = self.exchange.create_market_order(
                    symbol.upper(), side.lower(), amount, None, params
                )
            else:
                order = self.exchange.create_limit_order(
                    symbol.upper(), side.lower(), amount, price, params
                )
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            order = self.exchange.cancel_order(order_id, symbol.upper())
            return self._parse_order(order)
        except Exception as e:
            return {'error': str(e)}

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return [self._parse_order(o) for o in orders]
        except Exception:
            return []

    def _parse_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order data to common format"""
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
