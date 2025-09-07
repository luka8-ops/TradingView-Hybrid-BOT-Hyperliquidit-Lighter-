# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import signal
import sys
import traceback
from contextlib import asynccontextmanager
from app.webhook.tradingview_reciever import router as webhooks_router
from app.front_payload.frontend_router import router as frontend_router

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

# ✅ ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development
        # For production, specify your frontend domain:
        # "https://your-frontend-domain.supabase.co",
        # "https://your-custom-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# # ✅ PRODUCTION CORS SETTINGS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://your-supabase-project.supabase.co",
#         "https://your-custom-domain.com",
#         "http://localhost:3000",  # For local frontend development
#     ],
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],
#     allow_headers=["authorization", "x-api-key", "content-type"],
# )

# ✅ ADD GLOBAL EXCEPTION HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"❌ GLOBAL EXCEPTION: {exc}")
    logger.error(f"❌ Request: {request.url}")
    logger.error(f"❌ Traceback: {traceback.format_exc()}")
    return {"error": "Internal server error", "detail": str(exc)}

app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(frontend_router, tags=["Frontend Configuration"])

@app.get("/")
def read_root():
    return {"message": "Trading Bot API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}