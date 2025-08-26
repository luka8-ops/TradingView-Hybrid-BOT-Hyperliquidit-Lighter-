import logging
from app.websocket.track_account_balance import get_current_account_value
from app.websocket.get_coin_live_price import  get_coin_price

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def calculate_dynamic_position_size(symbol: str, sl_percent: float, leverage: int) -> float:
    """
    Calculate dynamic position size considering leverage.
    - Use 10% of account value for trading
    - Risk 2% of that 10% per trade (0.2% of total account)
    - Account for leverage in position sizing
    """
    try:
        # Get current account value and live price
        account_value = get_current_account_value()
        live_price = get_coin_price(symbol)
        
        if not live_price:
            logger.warning(f"No live price for {symbol}, using fallback")
            return 0.01  # Fallback minimum size
        
        # Calculate trading capital (10% of account)
        trading_capital = account_value * 0.10
        
        # Calculate risk amount (2% of trading capital)
        risk_amount = trading_capital * 0.02
        
        # Calculate position size in USD based on stop loss)
        position_notional_usd = risk_amount / (sl_percent / 100)
        
        # Convert to coin quantity (this is the actual position size you need to place)
        position_size_coins = position_notional_usd / live_price
        
        # Round to reasonable precision based on coin
        if symbol == "BTC":
            position_size_coins = round(position_size_coins, 3)  # 0.001 BTC precision
        elif symbol == "ETH":
            position_size_coins = round(position_size_coins, 3)  # 0.01 ETH precision
        else:
            position_size_coins = round(position_size_coins, 2)  # Default precision
        
        # Ensure minimum size
        min_size = 0.001 if symbol == "BTC" else 0.01
        position_size_coins = max(position_size_coins, min_size)
        
        # Calculate actual values for logging
        actual_notional = position_size_coins * live_price 
        actual_risk = actual_notional * (sl_percent / 100)
        
        logger.info(f"💰 Account: ${account_value:.2f}")
        logger.info(f"💼 Trading Capital (10%): ${trading_capital:.2f}")
        logger.info(f"⚠️ Risk Amount (2%): ${risk_amount:.2f}")
        logger.info(f"🪙 {symbol} Price: ${live_price:.2f}")
        logger.info(f"🔢 Leverage: {leverage}x")
        logger.info(f"📦 Position Size: {position_size_coins} {symbol}")
        logger.info(f"💵 Position Notional: ${actual_notional:.2f}")
        logger.info(f"📊 Actual Risk: ${actual_risk:.2f} ({(actual_risk / account_value) * 100:.3f}% of account)")
        
        return position_size_coins
        
    except Exception as e:
        logger.error(f"Error calculating dynamic position size: {e}")
        return 0.01  # Return minimum safe size