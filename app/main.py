# app/main.py
from fastapi import FastAPI
import asyncio
import logging
from contextlib import asynccontextmanager
from app.webhook.tradingview_reciever import router as webhooks_router
from app.websocket.account_tracker import account_tracker
from app.api.connection_manager import connection_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup & Shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Trading Bot API...")
    try:
        # Start account tracker in background
        await account_tracker.start()
        logger.info("✅ Account tracker initialized")
    except Exception as e:
        logger.error(f"❌ Failed to start account tracker: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trading Bot API...")
    try:
        # Unsubscribe from account updates
        await account_tracker.stop()
        logger.info("✅ Account tracker stopped")
        
        # Disconnect WebSocket
        address, info, exchange = connection_manager.get_connections()
        info.disconnect_websocket()
        logger.info("✅ WebSocket disconnected")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("✅ Shutdown completed")
    
app = FastAPI(
    title="Trading Bot API",
    description="Backend to receive TradingView webhooks and execute trades on Hyperliquid.",
    lifespan=lifespan
)

app.include_router(webhooks_router, tags=["Webhooks"])

@app.get("/")
def read_root():
    return {"message": "Trading Bot API is running."}

@app.get("/account-balance")
def get_balance():
    """Get current account balance"""
    from app.websocket.track_account_balance import get_current_account_value
    return {"account_value": get_current_account_value()}

