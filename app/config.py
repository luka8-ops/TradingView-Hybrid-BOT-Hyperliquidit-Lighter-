# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    HYPERLIQUID_SECRET_KEY: str
    HYPERLIQUID_ACCOUNT_ADDRESS: str
    TRADINGVIEW_PASSPHRASE: str

    class Config:
        pass

settings = Settings()
