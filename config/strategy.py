"""Local strategy configuration - user-modifiable trading parameters"""
from typing import Dict
from dataclasses import dataclass

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
        # Default config for all symbols (global settings)
        self._default_config = StrategyConfig()
        # Symbol-specific configs
        self._configs: Dict[str, StrategyConfig] = {}

    def get_config(self, symbol: str) -> StrategyConfig:
        """Get configuration for a symbol (symbol-specific or global default)"""
        if symbol not in self._configs:
            config = StrategyConfig(
                risk=self._default_config.risk,
                tp_percent=self._default_config.tp_percent,
                tp_count=self._default_config.tp_count,
                sl_percent=self._default_config.sl_percent,
                trailing_stop=self._default_config.trailing_stop,
                leverage=self._default_config.leverage,
            )
            self._configs[symbol] = config
            from config import yaml_persistence
            yaml_persistence.save_configs_to_yaml(self)
        return self._configs[symbol]

    def get_default_config(self) -> StrategyConfig:
        """Get global default configuration"""
        return self._default_config

    def set_default_config(self, config: StrategyConfig):
        """Set global default configuration"""
        self._default_config = config
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)

    def set_config(self, symbol: str, config: StrategyConfig):
        """Set configuration for a symbol"""
        self._configs[symbol] = config
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)

    def update_risk(self, symbol: str, risk: float) -> StrategyConfig:
        """Update risk for a symbol"""
        config = self.get_config(symbol)
        config.risk = max(0.0, min(1.0, risk))
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)
        return config

    def update_tp(self, symbol: str, tp_percent: float, tp_count: int) -> StrategyConfig:
        """Update take profit settings"""
        config = self.get_config(symbol)
        config.tp_percent = max(0.001, tp_percent)
        config.tp_count = max(1, tp_count)
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)
        return config

    def update_sl(self, symbol: str, sl_percent: float, use_trailing: bool = False) -> StrategyConfig:
        """Update stop loss settings"""
        config = self.get_config(symbol)
        config.sl_percent = max(0.001, sl_percent)
        config.trailing_stop = use_trailing
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)
        return config

    def update_leverage(self, symbol: str, leverage: int) -> StrategyConfig:
        """Update leverage for a symbol"""
        config = self.get_config(symbol)
        config.leverage = max(1, min(100, leverage))
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)
        return config

    def delete_config(self, symbol: str):
        """Remove symbol-specific configuration, falling back to global default"""
        if symbol in self._configs:
            del self._configs[symbol]
            from config import yaml_persistence
            yaml_persistence.save_configs_to_yaml(self)

    def reset_to_default(self, symbol: str):
        """Reset symbol-specific config to use global default"""
        self.delete_config(symbol)

    def update_global_default(self, **kwargs):
        """Update global default configuration with provided fields"""
        config = self._default_config
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        from config import yaml_persistence
        yaml_persistence.save_configs_to_yaml(self)
        return config

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


def _init_store():
    from config.yaml_persistence import init_store_from_yaml
    init_store_from_yaml(strategy_config_store)

_init_store()
