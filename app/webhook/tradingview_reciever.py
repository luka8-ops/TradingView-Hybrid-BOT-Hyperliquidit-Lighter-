# app/webhooks/tv_receiver.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from hyperliquid.utils import constants
from app.api.hyperliquid_api import setup
import logging

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str  # 'Buy' or 'Sell'
    leverage: int
    size: float
    tp_percent: float
    sl_percent: float

@router.post("/tradingview-webhook") 
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades on Hyperliquid.
    """
    logger.info(f"Received webhook payload: {payload.model_dump_json()}")

    if payload.passphrase != settings.TRADINGVIEW_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid passphrase")
    
    try:
        address, info, exchange = setup(constants.TESTNET_API_URL, skip_ws=True)
    except Exception as e:
        logger.error(f"Failed to setup Hyperliquid client: {e}")
        raise HTTPException(status_code=500, detail="Hyperliquid client setup failed.")

    try:
        # Map payload data to Hyperliquid parameters
        ticker = payload.symbol.replace("USDT", "") # 'ETHUSDT' -> 'ETH'
        is_buy = (payload.action.lower() == "buy")
        
        # Place the main order (Market order for simplicity)
        order_result = exchange.order(
            name=ticker, 
            is_buy=is_buy, 
            sz=payload.size, 
            limit_px=500000 if is_buy else 10000, # Aggressive price to ensure market execution
            order_type={"limit": {"tif": "Gtc"}}
        )
        logger.info(f"Main order placed: {order_result}")
        
        # Check if the order was filled before trying to access the price
        if 'filled' in order_result['response']['data']['statuses'][0]:
            avg_price = float(order_result['response']['data']['statuses'][0]['filled']['avgPx'])
            logger.info(f"Order filled at avg price: {avg_price}")
        else:
            logger.warning("Main order was not immediately filled. TP/SL not placed.")
            raise HTTPException(status_code=500, detail="Main order not immediately filled. TP/SL placement aborted.")
        
        # Get filled price from the order response
        avg_price = float(order_result['response']['data']['statuses'][0]['filled']['avgPx'])
        logger.info(f"Order filled at avg price: {avg_price}")

        # Update leverage
        exchange.update_leverage(payload.leverage, ticker)
        logger.info(f"Leverage updated to: {payload.leverage}")

        # Calculate TP/SL prices
        tp_price = avg_price * (1 + (payload.tp_percent / 100) / payload.leverage) if is_buy else avg_price * (1 - (payload.tp_percent / 100) / payload.leverage)
        sl_price = avg_price * (1 - (payload.sl_percent / 100) / payload.leverage) if is_buy else avg_price * (1 + (payload.sl_percent / 100) / payload.leverage)

        logger.info(f"Calculated TP Price: {tp_price}, SL Price: {sl_price}")
        
        # Place TP order
        tp_order_type = {"trigger": {"triggerPx": str(tp_price), "isMarket": False, "tpsl": "tp"}}
        tp_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=payload.size, 
            limit_px=str(tp_price), 
            order_type=tp_order_type, 
            reduce_only=True
        )
        logger.info(f"TP order placed: {tp_result}")

        # Place SL order
        sl_order_type = {"trigger": {"triggerPx": str(sl_price), "isMarket": False, "tpsl": "sl"}}
        sl_result = exchange.order(
            name=ticker, 
            is_buy=not is_buy, 
            sz=payload.size, 
            limit_px=str(sl_price), 
            order_type=sl_order_type, 
            reduce_only=True
        )
        logger.info(f"SL order placed: {sl_result}")

        return {"message": "Trade executed successfully on Hyperliquid."}

    except Exception as e:
        logger.error(f"Error executing trade on Hyperliquid: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")
