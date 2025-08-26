# app/webhooks/tv_receiver.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
import logging
from app.api.connection_manager import connection_manager
from app.websocket.track_account_balance import get_current_account_value
from app.websocket.get_coin_live_price import set_coins_to_track, get_coin_price, coins_to_track
router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str  # 'buy' or 'sell'
    leverage: int
    size: float
    tp_percent: float
    sl_percent: float
    tradingview_price: str

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

@router.post("/tradingview-webhook") 
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades on Hyperliquid.
    """
    logger.info(f"Received webhook payload: {payload.model_dump_json()}")

    if payload.passphrase != settings.TRADINGVIEW_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid passphrase")
    
    try:
        address, info, exchange = connection_manager.get_connections()
    except Exception as e:
        logger.error(f"Failed to setup Hyperliquid client: {e}")
        raise HTTPException(status_code=500, detail="Hyperliquid client setup failed.")

    user_state = info.user_state(address)
    has_position_for_coin = False
    positions = []
    symbol = payload.symbol.replace("USD", "")
    coins_to_track.append(symbol)
    set_coins_to_track(coins_to_track)
    live_coin_price = get_coin_price(symbol)
    print(f"Currently tracked prices: {live_coin_price}")

    for position in user_state["assetPositions"]:
        positions.append(position["position"])
        # Check if there's a position for our coin
        if position["position"]["coin"] == symbol:
            has_position_for_coin = True

    # Check if position exists for the coin before placing market order
    if has_position_for_coin:
        print(f"Position already open for {symbol}. Skipping market order.")
        return
    
    try:
        # Calculate dynamic position size WITH LEVERAGE
        dynamic_size = calculate_dynamic_position_size(symbol, payload.sl_percent, payload.leverage)
        logger.info(f"🎯 Using dynamic position size: {dynamic_size} {symbol}")
        
        # Map payload data to Hyperliquid parameters
        ticker = symbol
        is_buy = (payload.action.lower() == "buy")
        avg_price = None
        price_precision = 0
        tradingview_price = float(payload.tradingview_price)

        logger.info(f"TradingView trigger price: {tradingview_price}")

        # Update leverage
        exchange.update_leverage(payload.leverage, ticker, False)  # False = Isolated
        logger.info(f"Leverage updated to: {payload.leverage}")

        # Place the main order (Market order for simplicity)
        order_result = exchange.market_open(ticker, is_buy, dynamic_size)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                try:
                    filled = status["filled"]
                    avg_price = filled["avgPx"]
                    print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{avg_price}')
                except KeyError:
                    print(f'Error: {status["error"]}')

        logger.info(f"Main order placed: {order_result}")
        
        # Get filled price from the order response
        avg_price = float(order_result['response']['data']['statuses'][0]['filled']['avgPx'])
        logger.info(f"Order filled at avg price: {avg_price}")

        # Calculate TP/SL prices  
        tp_price = avg_price * (1 + (payload.tp_percent / 100)) if is_buy else avg_price * (1 - (payload.tp_percent / 100))
        sl_price = avg_price * (1 - (payload.sl_percent / 100)) if is_buy else avg_price * (1 + (payload.sl_percent / 100))

        # Round the calculated prices to the correct precision
        tp_price_rounded = round(tp_price, price_precision)
        sl_price_rounded = round(sl_price, price_precision)

        logger.info(f"Calculated TP Price: {tp_price_rounded}, SL Price: {sl_price_rounded}")
        
        # Place TP order
        tp_order_type = {"trigger": {"triggerPx": tp_price_rounded, "isMarket": True, "tpsl": "tp"}}
        tp_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=dynamic_size, 
            limit_px=7000, 
            order_type=tp_order_type, 
            reduce_only=True
        )
        logger.info(f"TP order placed: {tp_result}")

        # Place SL order
        sl_order_type = {"trigger": {"triggerPx": sl_price_rounded, "isMarket": True, "tpsl": "sl"}}
        sl_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=dynamic_size, 
            limit_px=1000, 
            order_type=sl_order_type, 
            reduce_only=True
        )
        logger.info(f"SL order placed: {sl_result}")

        return {"message": "Trade executed successfully on Hyperliquid."}

    except Exception as e:
        logger.error(f"Error executing trade on Hyperliquid: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")
