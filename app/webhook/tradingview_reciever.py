from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
import logging
from app.api.connection_manager import connection_manager
router = APIRouter()
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def clean_symbol(symbol: str) -> str:
    """Remove USD/USDT suffixes to get base symbol"""
    symbol = symbol.upper()
    if symbol.endswith("USDT"):
        return symbol[:-4]  # Remove last 4 characters (USDT)
    elif symbol.endswith("USD"):
        return symbol[:-3]  # Remove last 3 characters (USD)
    elif symbol.endswith("USDT.P"): 
        return symbol[:-6]  # Remove last 6 characters (USDT.P)
    return symbol  # Return as-is if no suffix

def get_price_precision(symbol: str) -> int:
    """Get appropriate price precision for different symbols"""
    if symbol in ["BTC", "ETH"]:
        return 0  # $50,123.0
    elif symbol in ["SOL"]:
        return 2  # $202.34
    elif symbol in ["NEAR", "DOT"]:
        return 3  # $12.456
    else:
        return 4  # $1.2345 (for smaller coins)

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str  # 'buy' or 'sell'
    leverage: int
    tp_percent: float
    sl_percent: float
    size: float
    tradingview_price: str

current_leverage = 20    # Default leverage

@router.post("/tradingview-webhook") 
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades on Hyperliquid.
    """
    logger.info(f"Received webhook payload: {payload.model_dump_json()}")
    received_payload_time = time.time()
    global current_leverage

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
    symbol = clean_symbol(payload.symbol)
    
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
        # Map payload data to Hyperliquid parameters
        size = payload.size
        ticker = symbol
        is_buy = (payload.action.lower() == "buy")
        avg_price = None
        price_precision = get_price_precision(symbol)
        tradingview_price = float(payload.tradingview_price)

        logger.info(f"TradingView trigger price: {tradingview_price}")
        
        # Update leverage
        if current_leverage != payload.leverage:
            current_leverage = payload.leverage
            exchange.update_leverage(payload.leverage, ticker, False)  # False = Isolated
            logger.info(f"Leverage updated to: {payload.leverage}")

        # Place the main order (Market order for simplicity)
        order_result = exchange.market_open(ticker, is_buy, size)
        latency = time.time() - received_payload_time
        logger.info(f"Order placement latency: {latency:.3f} seconds")
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
        logger.info(f"Difference between TradingView price and filled price: {abs(tradingview_price - avg_price)}")

        # Calculate TP/SL prices
        tp_price = avg_price * (1 + (payload.tp_percent / 100)) if is_buy else avg_price * (1 - (payload.tp_percent / 100))
        sl_price = avg_price * (1 - (payload.sl_percent / 100)) if is_buy else avg_price * (1 + (payload.sl_percent / 100))

        # Round the calculated prices to the correct precision
        tp_price_rounded = round(tp_price, price_precision)
        sl_price_rounded = round(sl_price, price_precision)

        logger.info(f"Calculated TP Price: {tp_price_rounded}, SL Price: {sl_price_rounded}")
        
        limit_price_mock = round(avg_price * 0.82)

        # Place TP order
        tp_order_type = {"trigger": {"triggerPx": tp_price_rounded, "isMarket": True, "tpsl": "tp"}}
        tp_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=size, 
            limit_px=limit_price_mock, 
            order_type=tp_order_type, 
            reduce_only=True
        )
        logger.info(f"TP order placed: {tp_result}")

        # Place SL order
        sl_order_type = {"trigger": {"triggerPx": sl_price_rounded, "isMarket": True, "tpsl": "sl"}}
        sl_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=size, 
            limit_px=limit_price_mock, 
            order_type=sl_order_type, 
            reduce_only=True
        )
        logger.info(f"SL order placed: {sl_result}")

        return {"message": "Trade executed successfully on Hyperliquid."}

    except Exception as e:
        logger.error(f"Error executing trade on Hyperliquid: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")
