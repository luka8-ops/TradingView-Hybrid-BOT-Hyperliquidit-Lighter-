import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info


from app.config import settings

def get_secret_key():
    secret_key = settings.HYPERLIQUID_SECRET_KEY
    if not secret_key:
        raise ValueError("Environment variable HYPERLIQUID_SECRET_KEY not set.")
    return secret_key

def setup(base_url=None, skip_ws=False, perp_dexs=None):
    secret_key = get_secret_key()
    account: LocalAccount = eth_account.Account.from_key(secret_key)
    
    address = settings.HYPERLIQUID_ACCOUNT_ADDRESS
    if not address:
        address = account.address
        print("Using wallet address as account address:", address)
    else:
        print("Running with account address:", address)
        
    if address != account.address:
        print("Running with agent address:", account.address)

    info = Info(base_url, skip_ws, perp_dexs=perp_dexs)
    user_state = info.user_state(address)
    spot_user_state = info.spot_user_state(address)
    margin_summary = user_state["marginSummary"]

    if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
        print("Not running the example because the provided account has no equity.")
        url = info.base_url.split(".", 1)[1]
        error_string = f"No accountValue:\nIf you think this is a mistake, make sure that {address} has a balance on {url}.\nIf address shown is your API wallet address, update the config to specify the address of your account, not the address of the API wallet."
        raise Exception(error_string)
    
    exchange = Exchange(account, base_url, vault_address="0x712fa55530c25d2502b66e87d178809e206a354f", account_address=address, perp_dexs=perp_dexs)
    return address, info, exchange