"""
Configuration for Phase 4 Matrix Simulation
"""

import os
import logging
from datetime import time

# --- Base Directory ---
BASE_DIR = os.path.dirname(__file__)

# --- TRADING MODE ---
MODE = "MOCK"
MOCK_NIFTY_FILE = os.path.join(BASE_DIR, "nifty_5min_last_year.csv")
MOCK_OPTIONS_FILE = os.path.join(BASE_DIR, "atm_daily_options_HYBRID_V3_ULTRA_FIXED.csv")
MOCK_SPEED_DELAY = 0.0  # Reduced delay for faster simulation
MOCK_DAYS_TO_REPLAY = 3
INCLUDE_TODAY = False # Explicitly exclude current day's data

# --- TRADING PARAMETERS ---
TRADING_INSTRUMENT = "NIFTY"
PRODUCT_TYPE = "INTRADAY"
ORDER_TYPE = "LIMIT"

# --- SESSION & API (Not used in MOCK) ---
SESSION_FILE = os.path.join(BASE_DIR, "upstox_session.json")
NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"

# --- STRATEGY & RISK ---
MAX_CONCURRENT_TRADES = 1
STOP_LOSS_PERCENT = 0.5
TARGET_PROFIT_PERCENT = 1.0

# --- DIRECTORIES ---
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TRADE_LOG_DIR = os.path.join(BASE_DIR, 'trade_logs')
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRADE_LOG_DIR, exist_ok=True)

# --- LOGGING & CONSOLE ---
LOG_LEVEL = "INFO"
CONSOLE_OUTPUT = True

# --- INDICATOR SETTINGS ---
CANDLE_BUFFER_SIZE = 500
INDICATOR_WARMUP_CANDLES = 50

# --- MARKET TIMINGS ---
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)
END_OF_DAY_SQUARE_OFF_TIME = time(15, 15)
