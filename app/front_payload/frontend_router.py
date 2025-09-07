from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from app.front_payload.trade_config import update_config, get_config, get_all_configs
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# API Key validation dependency
async def validate_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """Validate API key from Authorization header or X-API-Key header"""
    api_key = None
    
    # Check Authorization header (Bearer token)
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.replace("Bearer ", "")
    
    # Check X-API-Key header
    elif x_api_key:
        api_key = x_api_key
    
    # Validate the API key
    if not api_key or api_key != settings.API_KEY:
        logger.warning(f"❌ Invalid API key attempt: {api_key}")
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing API key"
        )
    
    logger.info("✅ API key validated successfully")
    return True

# Frontend configuration payload model
class FrontendConfigPayload(BaseModel):
    symbol: str
    leverage: Optional[int] = None
    tp_percent: Optional[float] = None
    sl_percent: Optional[float] = None
    size: Optional[float] = None

@router.post("/frontend-config")
async def update_frontend_config(
    payload: FrontendConfigPayload,
    authenticated: bool = Depends(validate_api_key)
):
    """Endpoint for frontend to send trading configuration updates"""
    try:
        logger.info(f"📝 Frontend config update: {payload.model_dump_json()}")
        
        # Update configuration
        updated_config = update_config(
            symbol=payload.symbol,
            leverage=payload.leverage,
            tp_percent=payload.tp_percent,
            sl_percent=payload.sl_percent,
            size=payload.size
        )
        
        return {
            "message": "Configuration updated successfully",
            "symbol": payload.symbol,
            "config": updated_config
        }
        
    except Exception as e:
        logger.error(f"❌ Config update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/frontend-config/{symbol}")
async def get_frontend_config(
    symbol: str,
    authenticated: bool = Depends(validate_api_key)
):
    """Get current configuration for a symbol"""
    try:
        config = get_config(symbol)
        return {
            "symbol": symbol.upper(),
            "config": config
        }
    except Exception as e:
        logger.error(f"❌ Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-config")
async def get_all_frontend_configs(
    authenticated: bool = Depends(validate_api_key)
):
    """Get all configurations"""
    try:
        configs = get_all_configs()
        return {
            "configs": configs
        }
    except Exception as e:
        logger.error(f"❌ Error getting all configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
