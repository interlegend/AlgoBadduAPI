import os
import sys
import json
import logging
from datetime import datetime

# Add necessary paths
sys.path.append(r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-3')
sys.path.append(r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\UPSTOX-API')

from atm_selector import ATMSelector
from config_live import SESSION_FILE

# Basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

def run_smoke_test():
    """
    Smoke test to verify Phase-3 upgrade.
    1. Fetches NIFTY spot price.
    2. Resolves ATM CE & PE symbols.
    3. Confirms component initialization.
    """
    logging.info("--- Phase-3 Smoke Test ---")
    
    # 1. Load access token
    try:
        with open(SESSION_FILE, 'r') as f:
            access_token = json.load(f).get('access_token')
        if not access_token:
            raise ValueError("Access token not found.")
        logging.info("✅ Access token loaded.")
    except Exception as e:
        logging.error(f"❌ Failed to load access token: {e}")
        logging.error("Please ensure a valid session file exists.")
        return

    # 2. Initialize ATMSelector and fetch data
    try:
        atm_selector = ATMSelector(access_token)
        if atm_selector.initialize_atm():
            config = atm_selector.get_current_config()
            logging.info("✅ ATM Selector initialized.")
            logging.info(f"   - NIFTY Spot: {atm_selector.get_nifty_spot()}")
            logging.info(f"   - ATM Strike: {config['strike']}")
            logging.info(f"   - ATM CE: {config['ce_key']}")
            logging.info(f"   - ATM PE: {config['pe_key']}")
            logging.info("✅ Smoke test passed!")
        else:
            logging.error("❌ ATM Selector failed to initialize.")
    except Exception as e:
        logging.error(f"❌ An error occurred during the smoke test: {e}")

if __name__ == "__main__":
    run_smoke_test()
