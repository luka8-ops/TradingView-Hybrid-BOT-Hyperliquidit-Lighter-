# app/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    HYPERLIQUID_SECRET_KEY: str
    HYPERLIQUID_ACCOUNT_ADDRESS: str
    TRADINGVIEW_PASSPHRASE: str
    HYPERLIQUID_VAULT_ADDRESS: str
    API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
