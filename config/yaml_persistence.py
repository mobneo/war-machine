"""YAML persistence for strategy configurations"""
import os
from pathlib import Path
from typing import Dict, Optional
import yaml

from config.strategy import StrategyConfig, StrategyConfigStore, strategy_config_store


CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "strategies.yml"


def _config_to_dict(config: StrategyConfig) -> Dict:
    result = config.to_dict()
    result['tp_count'] = config.tp_count
    result['trailing_stop'] = config.trailing_stop
    return result


def _dict_to_config(data: Dict) -> StrategyConfig:
    return StrategyConfig(
        risk=data.get('risk', 0.01),
        tp_percent=data.get('tp_percent', 0.02),
        tp_count=data.get('tp_count', 1),
        sl_percent=data.get('sl_percent', 0.01),
        trailing_stop=data.get('trailing_stop', False),
        leverage=data.get('leverage', 10),
    )


def load_configs_from_yaml() -> Dict[str, StrategyConfig]:
    """Load all configurations from YAML file"""
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, 'r') as f:
        data = yaml.safe_load(f) or {}

    configs = {}
    symbols_data = data.get('symbols', {})
    for symbol, symbol_config in symbols_data.items():
        if symbol_config:
            configs[symbol] = _dict_to_config(symbol_config)

    return configs


def save_configs_to_yaml(store: StrategyConfigStore):
    """Save all configurations to YAML file"""
    data = {
        'global': _config_to_dict(store.get_default_config()),
        'symbols': {
            symbol: _config_to_dict(config)
            for symbol, config in store.get_all_configs().items()
        }
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def init_store_from_yaml(store: StrategyConfigStore):
    """Initialize store with configs from YAML file"""
    configs = load_configs_from_yaml()

    if 'global' in configs:
        store.set_default_config(configs.pop('global'))

    for symbol, config in configs.items():
        store.set_config(symbol, config)


def update_store_from_yaml(store: StrategyConfigStore, symbol: Optional[str] = None):
    """Update store from YAML file

    If symbol is None - reload all configs from YAML
    If symbol is provided - reload only that symbol's config
    """
    configs = load_configs_from_yaml()

    if symbol is None:
        init_store_from_yaml(store)
        return

    if symbol in configs:
        store.set_config(symbol, configs[symbol])
    elif CONFIG_FILE.exists():
        symbol_configs = configs.get('symbols', {})
        if symbol in symbol_configs:
            store.set_config(symbol, symbol_configs[symbol])
