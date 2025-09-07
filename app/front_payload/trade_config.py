# Simple dictionary to store trading configurations per symbol
# Format: {"SYMBOL": {"leverage": 20, "tp_percent": 2.0, "sl_percent": 1.0, "size": 0.1}}

trading_configs = {}

def update_config(symbol: str, leverage: int = None, tp_percent: float = None, 
                 sl_percent: float = None, size: float = None):
    """Update trading configuration for a symbol"""
    symbol = symbol.upper()
    
    if symbol not in trading_configs:
        # Default values
        trading_configs[symbol] = {
            "leverage": 20,
            "tp_percent": 2.0,
            "sl_percent": 1.0,
            "size": 0.1
        }
    
    # Update only provided values
    if leverage is not None:
        trading_configs[symbol]["leverage"] = leverage
    if tp_percent is not None:
        trading_configs[symbol]["tp_percent"] = tp_percent
    if sl_percent is not None:
        trading_configs[symbol]["sl_percent"] = sl_percent
    if size is not None:
        trading_configs[symbol]["size"] = size
    
    return trading_configs[symbol]

def get_config(symbol: str):
    """Get trading configuration for a symbol (returns defaults if not set)"""
    symbol = symbol.upper()
    
    if symbol not in trading_configs:
        # Return default values
        trading_configs[symbol] = {
            "leverage": 20,
            "tp_percent": 2.0,
            "sl_percent": 1.0,
            "size": 0.1
        }
    
    return trading_configs[symbol]

def get_all_configs():
    """Get all trading configurations"""
    return trading_configs
