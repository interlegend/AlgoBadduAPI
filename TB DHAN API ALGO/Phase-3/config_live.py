"""
LIVE TRADING CONFIGURATION
Strategy V27 - BUY ONLY Mode

SIMPLIFIED VERSION - Direct paths!
"""

from datetime import time

# ==================== DIRECT FILE PATHS (EDIT THESE!) ====================

# 🔥 YOUR SESSION FILE - PASTE FULL PATH HERE!
SESSION_FILE = r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\UPSTOX-API\upstox_session.json'

# 🔥 WHERE TO SAVE LOGS
LOG_DIR = r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-3\logs'
TRADE_LOG_DIR = r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-3\trade_logs'

# ==================== UPSTOX API ====================
UPSTOX_API_VERSION = "v2"
UPSTOX_WS_URL = "wss://api.upstox.com/v2/feed/market-data-feed/authorize"

# ==================== MARKET HOURS ====================
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
PRE_MARKET_START = time(9, 0)
ENTRY_WINDOW_START = time(9, 30)
ENTRY_WINDOW_END = time(15, 15)
EOD_EXIT_TIME = time(15, 25)

# ==================== INSTRUMENTS ====================
NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"
NIFTY_INDEX_TOKEN = "Nifty 50"

# ==================== STRATEGY PARAMETERS ====================
LOT_SIZE = 75
CANDLE_INTERVAL = "5minute"
INDICATOR_WARMUP_CANDLES = 50

# ==================== PAPER TRADING ====================
VIRTUAL_CAPITAL = 50000
MAX_POSITIONS = 3
SIMULATED_SLIPPAGE_TICKS = 0

# ==================== RISK MANAGEMENT ====================
DAILY_LOSS_LIMIT = -5000
DAILY_PROFIT_TARGET = 10000

# ==================== LOGGING ====================
LOG_LEVEL = "INFO"
CONSOLE_OUTPUT = True
SAVE_TICK_DATA = False

# ==================== WEBSOCKET ====================
WS_RECONNECT_DELAY = 5
WS_MAX_RECONNECT_ATTEMPTS = 10
WS_PING_INTERVAL = 30

# ==================== DATA RETENTION ====================
CANDLE_BUFFER_SIZE = 100
CLEANUP_OLD_LOGS_DAYS = 7

# ==================== AUTO-CREATE FOLDERS ====================
import os
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRADE_LOG_DIR, exist_ok=True)