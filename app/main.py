# app/main.py
from fastapi import FastAPI
import asyncio
import logging
import signal
import sys
import traceback
from contextlib import asynccontextmanager
from app.webhook.tradingview_reciever import router as webhooks_router

logging.basicConfig(level=logging.INFO)  # Change to INFO to see what's happening
logger = logging.getLogger(__name__)

# ✅ ADD EXCEPTION HANDLER
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.error("❌ UNCAUGHT EXCEPTION:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# Startup & Shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup 
    logger.info("🚀 Starting Trading Bot API...")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trading Bot API...")
    logger.info("✅ Shutdown completed")

app = FastAPI(
    title="Trading Bot API",
    description="Backend to receive TradingView webhooks and execute trades on Hyperliquid.",
    lifespan=lifespan  # Re-enable this to see shutdown logs
)

# ✅ ADD GLOBAL EXCEPTION HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"❌ GLOBAL EXCEPTION: {exc}")
    logger.error(f"❌ Request: {request.url}")
    logger.error(f"❌ Traceback: {traceback.format_exc()}")
    return {"error": "Internal server error", "detail": str(exc)}

app.include_router(webhooks_router, tags=["Webhooks"])

@app.get("/")
def read_root():
    return {"message": "Trading Bot API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}