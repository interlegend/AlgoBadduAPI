"""
Configuration for Phase 3 Live Paper Trading
"""

import os
import json
import logging
from datetime import time

# --- PATHS ---
# Get Project Root (Assuming we are in Algo Baddu Trading API/Phase-3/)
# __file__ = .../Phase-3/config_live.py -> dirname = .../Phase-3 -> dirname = .../Algo Baddu Trading API
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Session File Path (Corrected)
SESSION_FILE = os.path.join(PROJECT_ROOT, "UPSTOX-API", "upstox_session.json")

# --- LOAD SESSION ---
UPSTOX_ACCESS_TOKEN = None
try:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
            UPSTOX_ACCESS_TOKEN = session_data.get("access_token")
            print(f"✅ Loaded Access Token from: {SESSION_FILE}")
    else:
        print(f"❌ Session file not found at: {SESSION_FILE}")
except Exception as e:
    print(f"❌ Failed to load Upstox Session: {e}")

# --- TRADING MODE ---
MODE = "LIVE"

# --- TRADING ASSET CONFIGURATION ---
# Supported: 'NIFTY', 'CRUDEOIL', 'NATURALGAS'
TRADING_ASSET = "NIFTY"  # Default, updated by main menu

# --- TRADING PARAMETERS ---
PRODUCT_TYPE = "INTRADAY"
ORDER_TYPE = "LIMIT"
NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"

# Dynamic Keys (Populated at Runtime)
MCX_KEYS = {
    'CRUDEOIL': {'key': None, 'lot_size': 100},
    'NATURALGAS': {'key': None, 'lot_size': 1250}
}

# --- LOGGING ---
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TRADE_LOG_DIR = os.path.join(BASE_DIR, 'trade_logs')
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRADE_LOG_DIR, exist_ok=True)

# --- INDICATOR SETTINGS ---
CANDLE_BUFFER_SIZE = 500
INDICATOR_WARMUP_CANDLES = 50

# --- MARKET TIMINGS ---
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)
END_OF_DAY_SQUARE_OFF_TIME = time(15, 15)