import asyncio
import logging
from app.api.hyperliquid_api import setup
from app.websocket.track_account_balance import handle_websocket_data
from app.websocket.get_coin_live_price import handle_allmids_data
from hyperliquid.utils import constants
from app.api.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class AccountTracker:
    def __init__(self):
        self.address = None
        self.info = None
        self.exchange = None
        self.account_subscription = None 
        self.account_subscription_status = None
        self.price_subscription = None 
        self.price_subscription_status = None

    async def start(self):
        """Start the account tracking service"""
        try:
            self.address, self.info, self.exchange = connection_manager.get_connections()
            logger.info(f"Starting account tracker for address: {self.address}")
            
            # Create account_subscription object AFTER getting the address
            self.account_subscription = {"type": "webData2", "user": self.address}
            self.price_subscription = {"type": "allMids"}
            
            # Subscribe to webData2 for real-time account updates
            self.account_subscription_status = self.info.subscribe(self.account_subscription, handle_websocket_data)
            self.price_subscription_status = self.info.subscribe(self.price_subscription, handle_allmids_data)

            logger.info(f"✅ Account tracker started successfully. account_subscription status: {self.account_subscription_status}, price_subscription status: {self.price_subscription_status}")

        except Exception as e:
            logger.error(f"❌ Failed to start account tracker: {e}")
            raise
    
    async def stop(self):
        """Stop the account tracking service"""
        try:
            if self.info and self.account_subscription and self.account_subscription_status:
                self.info.unsubscribe(self.account_subscription, self.account_subscription_status)
                self.info.unsubscribe(self.price_subscription, self.price_subscription_status)
                logger.info("✅ Account tracker account_subscription stopped")
            else:
                logger.warning("⚠️ Account tracker was not properly initialized, skipping unsubscribe")

        except Exception as e:
            logger.error(f"❌ Error stopping account tracker: {e}")
        finally:
            logger.info("Account tracker stopped")

# Global instance
# account_tracker = AccountTracker()

    # try:
    #     # Unsubscribe from account updates
    #     await account_tracker.stop()
    #     logger.info("✅ Account tracker stopped")
        
    #     # Disconnect WebSocket
    #     address, info, exchange = connection_manager.get_connections()
    #     info.disconnect_websocket()
    #     logger.info("✅ WebSocket disconnected")
        
    # except Exception as e:
    #     logger.error(f"❌ Error during shutdown: {e}")

    # try:
    #     # Unsubscribe from account updates
    #     await account_tracker.stop()
    #     logger.info("✅ Account tracker stopped")
        
    #     # Disconnect WebSocket
    #     address, info, exchange = connection_manager.get_connections()
    #     info.disconnect_websocket()
    #     logger.info("✅ WebSocket disconnected")
        
    # except Exception as e:
    #     logger.error(f"❌ Error during shutdown: {e}")
    