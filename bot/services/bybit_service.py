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
        except Exception as e:
            return []

    def _parse_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Parse position data to common format"""
        try:
            return {
                'symbol': position.get('symbol', position.get('symbolName')),
                'side': position.get('side', position.get('positionSide')),
                'size': float(position.get('size', position.get('positionQty', 0))),
                'entry_price': float(position.get('entryPrice', position.get('avgPrice', 0))),
                'liq_price': float(position.get('liqPrice', position.get('liqPrice', 0))),
                'margin': float(position.get('positionValue', position.get('positionMargin', 0))),
                'roee': float(position.get('realisedRoe', position.get('roee', 0))),
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
