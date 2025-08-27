import time
from hyperliquid.utils import constants
from datetime import datetime

# Global variable to track account value
current_account_value = 1000

def get_current_account_value():
    """Get the current account value"""
    return current_account_value

def handle_websocket_data(data):
    """Extract account value from webData2 subscription"""
    global current_account_value  # Declare global inside the function
    
    try:
        # Add timestamp to see when updates arrive
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
        # print(f"🕒 Update received at: {timestamp}")
        
        if isinstance(data, dict) and data.get('channel') == 'webData2':
            web_data = data.get('data', {})            
            # Navigate to account value: webData2 -> data -> clearinghouseState -> marginSummary -> accountValue
            margin_summary = web_data['clearinghouseState']['marginSummary']
            account_value = float(margin_summary.get('accountValue', '0'))
            # total_margin_used = float(margin_summary.get('totalMarginUsed', '0'))
            # total_raw_usd = float(margin_summary.get('totalRawUsd', '0'))
            # print(f"📊 Margin Used: ${total_margin_used:.2f}")
            # print(f"📊 Raw USD: ${total_raw_usd:.2f}")
            # print(f"✅ ACCOUNT VALUE: ${account_value:.2f}")
            if abs(account_value - current_account_value) > 0.01:  # Only log significant changes
                print(f"🔄 Account value changed: ${current_account_value:.2f} → ${account_value:.2f}")
                current_account_value = account_value
            else:
                current_account_value = account_value  # Still update the value
                # print(f"📍 No significant change (threshold: $0.01)")
        else:
            print(f"❌ Unexpected data format: {data}")
            
        
    except Exception as e:
        print(f"❌ Error extracting account value: {e}")
