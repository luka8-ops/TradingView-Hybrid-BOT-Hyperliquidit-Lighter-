# app/webhooks/tv_receiver.py
import asyncio
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from hyperliquid.utils import constants
from app.api.hyperliquid_api import setup
import logging
import time

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
        unique_id = str(uuid.uuid4())
        
        # Place the main order (Market order for simplicity)
        order_result = exchange.order(
            name=ticker, 
            is_buy=is_buy, 
            sz=payload.size, 
            limit_px=1000000 if is_buy else 0.01, # Aggressive price
            order_type={"limit": {"tif": "Gtc"}},
            cloid=unique_id
        )
        logger.info(f"Main order placed: {order_result}")
        
        avg_price = None
        try:
            status = order_result['response']['data']['statuses'][0]
            if 'filled' in status:
                avg_price = float(status['filled']['avgPx'])
                logger.info(f"Order filled immediately at avg price: {avg_price}")
            else:
                avg_price = await get_filled_price(info, address, unique_id)
                if avg_price is None:
                    raise Exception("Order not filled within timeout.")
                logger.info(f"Order filled after polling at avg price: {avg_price}")
        
        except Exception as e:
            logger.error(f"Error checking order status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get order fill status: {e}")

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
            limit_px=tp_price,
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
            limit_px=sl_price,
            order_type=sl_order_type, 
            reduce_only=True
        )
        logger.info(f"SL order placed: {sl_result}")

        return {"message": "Trade executed successfully on Hyperliquid."}

    except Exception as e:
        logger.error(f"Error executing trade on Hyperliquid: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")

async def get_filled_price(info, address: str, unique_id: str, timeout_seconds: int = 10):
    """
    Polls the fills history to find the filled price for a specific id.
    """
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        fills_history = info.user_fills(address)
        for fill in fills_history:
            if fill.get('cloid') == unique_id:
                return float(fill['px'])
        await asyncio.sleep(1)
    return None