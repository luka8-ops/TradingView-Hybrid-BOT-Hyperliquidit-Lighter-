from app.api.hyperliquid_api import setup
from hyperliquid.utils import constants
import logging

logger = logging.getLogger(__name__)

# Single connection: Only one Hyperliquid connection across your entire app
# Shared state: All parts of your app use the same address, info, exchange
# Resource efficiency: Avoid multiple API connections
class ConnectionManager:
    _instance = None
    
    def __new__(cls):
        """Checks if this is the first time creating the class,
           Creates the actual object instance (only once), 
           Returns the same instance every time
        """
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.address = None
            self.info = None
            self.exchange = None
            self._initialized = False
    
    def initialize(self):
        """Initialize connections if not already done"""
        if not self._initialized:
            try:
                self.address, self.info, self.exchange = setup(constants.TESTNET_API_URL, skip_ws=True)
                self._initialized = True
                logger.info(f"✅ Connection manager initialized for address: {self.address}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize connections: {e}")
                raise
        return self.address, self.info, self.exchange
    
    def get_connections(self):
        """Get existing connections or initialize if needed"""
        if not self._initialized:
            return self.initialize()
        return self.address, self.info, self.exchange

# Global instance
connection_manager = ConnectionManager()