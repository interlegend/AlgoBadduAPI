"""
Configuration for Phase 3 Live Paper Trading
"""

import os
import logging
from datetime import time

# --- TRADING MODE ---
# This is the live trading configuration.
MODE = "LIVE"

# --- TRADING PARAMETERS ---
TRADING_INSTRUMENT = "NIFTY"
PRODUCT_TYPE = "INTRADAY"
ORDER_TYPE = "LIMIT"

# --- SESSION & API ---
SESSION_FILE = r"C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\UPSTOX-API\upstox_session.json"
NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"

# --- STRATEGY & RISK ---
MAX_CONCURRENT_TRADES = 1
STOP_LOSS_PERCENT = 0.5
TARGET_PROFIT_PERCENT = 1.0

# --- DIRECTORIES ---
BASE_DIR = os.path.dirname(__file__)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TRADE_LOG_DIR = os.path.join(BASE_DIR, 'trade_logs')

# Create directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRADE_LOG_DIR, exist_ok=True)

# --- LOGGING & CONSOLE ---
LOG_LEVEL = "INFO"
CONSOLE_OUTPUT = True

# --- INDICATOR SETTINGS ---
CANDLE_BUFFER_SIZE = 100
INDICATOR_WARMUP_CANDLES = 50

# --- MARKET TIMINGS ---
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)
END_OF_DAY_SQUARE_OFF_TIME = time(15, 15)
