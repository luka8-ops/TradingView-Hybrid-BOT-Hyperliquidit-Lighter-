import time
from hyperliquid.utils import constants
from datetime import datetime

# Global variable to store mid prices for specific coins
tracked_coins = {}  # Will store {coin: price}
coins_to_track = {'BTC', 'ETH', 'SOL'}  # List of coins we want to track

def set_coins_to_track(coin_list):
    """Set which coins you want to track dynamically"""
    global coins_to_track
    coins_to_track = {coin.upper() for coin in coin_list}  # Convert to uppercase
    print(f"📍 Now tracking coins: {coins_to_track}")

def add_coin_to_track(coin):
    """Add a single coin to tracking set - only function you actually need"""
    global coins_to_track
    coin_upper = coin.upper()
    coins_to_track.add(coin_upper)  # Automatically handles duplicates
    print(f"📍 Added {coin_upper} to tracking. Total: {len(coins_to_track)} coins")

def get_coin_price(coin):
    """Get the current mid price for a specific coin"""
    return tracked_coins.get(coin.upper(), 0.0)

def get_all_tracked_prices():
    """Get all currently tracked coin prices"""
    return tracked_coins.copy()

def handle_allmids_data(data):
    """Handle allMids subscription data and extract specific coins"""
    global tracked_coins
    
    try:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        if isinstance(data, dict) and data.get('channel') == 'allMids':
            mids_data = data['data']['mids']
            
            if isinstance(mids_data, dict) and coins_to_track:
                print(f"💹 Price update at: {timestamp}")

                # Extract only the coins we want to track
                updated_prices = {}
                for coin in coins_to_track:
                    if coin in mids_data:
                        price = float(mids_data[coin])
                        updated_prices[coin] = price
                        print(f"   • {coin}: ${price:,.4f}")
                
                # Update global tracked prices
                tracked_coins.update(updated_prices)
                    
            elif not coins_to_track:
                print("⚠️ No coins specified to track. Use set_coins_to_track(['BTC', 'ETH', ...]) first")
                
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error handling allMids data: {e}")