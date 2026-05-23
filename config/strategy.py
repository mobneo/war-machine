"""Local strategy configuration - user-modifiable trading parameters"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    """Trading strategy configuration for a specific symbol"""
    risk: float = 0.01  # Risk per trade (decimal, e.g., 0.01 = 1%)
    tp_percent: float = 0.02  # Take profit in percent
    tp_count: int = 1  # Number of take profit orders
    sl_percent: float = 0.01  # Stop loss in percent
    trailing_stop: bool = False  # Use trailing stop instead of regular SL
    leverage: int = 10  # Leverage for the symbol

    def to_dict(self) -> Dict:
        return {
            'risk': self.risk,
            'tp_percent': self.tp_percent,
            'tp_count': self.tp_count,
            'sl_percent': self.sl_percent,
            'trailing_stop': self.trailing_stop,
            'leverage': self.leverage,
        }


class StrategyConfigStore:
    """Store for symbol-specific strategy configurations"""

    def __init__(self):
        # Default config for all symbols
        self._configs: Dict[str, StrategyConfig] = {}

    def get_config(self, symbol: str) -> StrategyConfig:
        """Get configuration for a symbol"""
        if symbol not in self._configs:
            self._configs[symbol] = StrategyConfig()
        return self._configs[symbol]

    def set_config(self, symbol: str, config: StrategyConfig):
        """Set configuration for a symbol"""
        self._configs[symbol] = config

    def update_risk(self, symbol: str, risk: float) -> StrategyConfig:
        """Update risk for a symbol"""
        config = self.get_config(symbol)
        config.risk = max(0.0, min(1.0, risk))  # Clamp between 0 and 1
        return config

    def update_tp(self, symbol: str, tp_percent: float, tp_count: int) -> StrategyConfig:
        """Update take profit settings"""
        config = self.get_config(symbol)
        config.tp_percent = max(0.001, tp_percent)
        config.tp_count = max(1, tp_count)
        return config

    def update_sl(self, symbol: str, sl_percent: float, use_trailing: bool = False) -> StrategyConfig:
        """Update stop loss settings"""
        config = self.get_config(symbol)
        config.sl_percent = max(0.001, sl_percent)
        config.trailing_stop = use_trailing
        return config

    def update_leverage(self, symbol: str, leverage: int) -> StrategyConfig:
        """Update leverage for a symbol"""
        config = self.get_config(symbol)
        config.leverage = max(1, min(100, leverage))  # Clamp between 1 and 100
        return config

    def delete_config(self, symbol: str):
        """Remove symbol-specific configuration"""
        if symbol in self._configs:
            del self._configs[symbol]

    def get_all_configs(self) -> Dict[str, StrategyConfig]:
        """Get all configurations"""
        return self._configs.copy()


# Global instance
strategy_config_store = StrategyConfigStore()


def get_strategy_config(symbol: str) -> StrategyConfig:
    """Convenience function to get strategy config for a symbol"""
    return strategy_config_store.get_config(symbol)


def set_strategy_config(symbol: str, config: StrategyConfig):
    """Convenience function to set strategy config for a symbol"""
    strategy_config_store.set_config(symbol, config)
