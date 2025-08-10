# app/main.py
from fastapi import FastAPI
from app.webhook.tradingview_reciever import router as webhooks_router

app = FastAPI(
    title="Trading Bot API",
    description="Backend to receive TradingView webhooks and execute trades on Bybit V5."
)

# app.add_middleware(IPWhitelistMiddleware)     
app.include_router(webhooks_router, tags=["Webhooks"])  

@app.get("/")
def read_root():
    return {"message": "Trading Bot API is running."}