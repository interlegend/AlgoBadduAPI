"""
LIVE TRADER MAIN - PHASE 3 (DEPLOYMENT)
Integrates Real Strategy V30 + Live Upstox Data + Warm-Up Logic
"""

import time
import logging
import json
import sys
import os
from datetime import datetime
import pandas as pd

# Force UTF-8 encoding for Windows Console
sys.stdout.reconfigure(encoding='utf-8')

# === IMPORT CORE MODULES ===
from config_live import UPSTOX_ACCESS_TOKEN, PROJECT_ROOT
from live_data_streamer import LiveDataStreamer
from indicator_calculator import IndicatorCalculator
from live_signal_scanner import LiveSignalScanner
from paper_order_manager import PaperOrderManager
from trade_logger import TradeLogger
from position_tracker import PositionTracker
from atm_selector import ATMSelector # Assuming this exists or we need to copy it? 
# Wait, Step 2 prompt said: "Phase 3 must use atm_selector.py". 
# I see 'atm_selector.py' in Phase 3 file list. I should trust it exists.

# Setup Logging
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"live_trader_{datetime.now().strftime('%Y%m%d')}.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_instrument_keys():
    """
    Dynamic ATM Selector for Live Trading.
    1. Fetch NIFTY Spot Price (we need a way to get this, or just hardcode a rough ATM for start)
    Actually, for the websocket to start, we need keys.
    We can fetch NIFTY key static, but CE/PE keys change.
    
    Solution:
    We will start with NIFTY only.
    Then, once we get the first NIFTY tick, we can dynamically subscribe to ATM options?
    
    OR, simpler for now:
    Use ATMSelector to find keys based on 'previous close' or just rely on the user/config?
    
    Let's stick to the prompt instructions.
    "Real Option Prices: Unlike Phase 4... Phase 3 must use atm_selector.py to find the real ATM strike and subscribe..."
    
    I will use ATMSelector to get the keys.
    """
    # For initialization, we might need to fetch spot first.
    # Let's assume ATMSelector handles this or we pass a hardcoded valid NIFTY key.
    
    # NIFTY 50 Index Key (Static)
    NIFTY_KEY = "NSE_INDEX|Nifty 50"
    
    # We need CE and PE keys.
    # Let's initialize ATMSelector.
    # Ideally, we should fetch the current NIFTY spot from Upstox API first.
    # But for now, let's assume the Streamer can handle dynamic subscription later? 
    # The Streamer in Phase 3 expects keys in __init__.
    
    # Hack for startup: Use a recent known ATM or fetch it.
    # Let's try to fetch NIFTY Quote to get LTP.
    import requests
    url = "https://api.upstox.com/v2/market-quote/ltp?instrument_key=NSE_INDEX|Nifty 50"
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    
    ce_key = None
    pe_key = None
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            nifty_ltp = data['data']['NSE_INDEX:Nifty 50']['last_price']
            logger.info(f"✅ Current NIFTY Spot: {nifty_ltp}")
            
            # Select ATM keys
            selector = ATMSelector(UPSTOX_ACCESS_TOKEN)
            atm_strike, ce_key, pe_key = selector.get_atm_keys(nifty_ltp)
            logger.info(f"🎯 Selected ATM Strike: {atm_strike} | CE: {ce_key} | PE: {pe_key}")
            
        else:
            logger.error("❌ Failed to fetch NIFTY spot for ATM selection.")
            
    except Exception as e:
        logger.error(f"💥 Error fetching initial ATM keys: {e}")

    return {
        'nifty': NIFTY_KEY,
        'ce': ce_key,
        'pe': pe_key
    }

def main():
    print("="*70)
    print("🚀 TRADER-BADDU LIVE TRADER (PHASE 3) - INITIALIZING...")
    print("="*70)
    
    # 1. Initialize Components
    trade_logger = TradeLogger(os.path.join(PROJECT_ROOT, "trade_logs"))
    position_tracker = PositionTracker()
    
    indicator_calculator = IndicatorCalculator(buffer_size=500) # Verified 500
    signal_scanner = LiveSignalScanner(indicator_calculator, position_tracker)
    
    # Strategy Instance (for Order Manager)
    from strategy_v30 import StrategyV30
    strategy = StrategyV30()
    order_manager = PaperOrderManager(strategy, position_tracker, trade_logger)
    
    # 2. Get Instrument Keys (ATM)
    keys = load_instrument_keys()
    if not keys['ce'] or not keys['pe']:
        logger.error("❌ CRITICAL: Could not determine ATM keys. Exiting.")
        return

    # --- SIGNAL CALLBACK WRAPPER ---
    def signal_handler_callback(candle_type):
        """
        Wrapper to bridge Signal Scanner and Order Manager.
        Executed by Data Streamer thread on candle close.
        """
        # 1. Detect Signal
        signal = signal_scanner.on_candle_closed(candle_type)
        
        # 2. Route to Order Manager if Valid
        if signal:
            # Get signal timestamp from indicators
            nifty_data = indicator_calculator.get_nifty_indicators()
            signal_time = nifty_data.get('timestamp', datetime.now())
            
            logger.info(f"🔗 BRIDGE: Routing {signal} @ {signal_time} to Order Manager")
            order_manager.on_signal_detected(signal, signal_time)

    # 3. Initialize Data Streamer with Warm-Up
    data_streamer = LiveDataStreamer(
        access_token=UPSTOX_ACCESS_TOKEN,
        instrument_keys=keys,
        indicator_calculator=indicator_calculator,
        on_candle_closed_callback=signal_handler_callback
    )
    
    # 4. EXECUTE WARM-UP (The Time Machine)
    print("\n⏳ EXECUTING WARM-UP SEQUENCE...")
    data_streamer.initialize_warmup(days=5)
    
    # 5. START LIVE STREAMING
    print("\n🔌 CONNECTING TO LIVE WEBSOCKET...")
    if not data_streamer.start_websocket():
        logger.error("❌ Failed to connect to WebSocket. Exiting.")
        return

    logger.info("✅ SYSTEM LIVE. WAITING FOR TICKS...")
    
    last_tick_time = datetime.now()
    
    try:
        while True:
            # === THE HEARTBEAT LOOP ===
            current_time = datetime.now()
            
            # Check Market Hours (Exit if past 15:35)
            if current_time.time() > datetime.strptime("15:35", "%H:%M").time() and current_time.time() < datetime.strptime("23:59", "%H:%M").time():
                 # Simple check, assuming we started today. 
                 # If running 24/7 on server, we might need better logic, but for local script:
                 logger.info("🌙 Market Closed (Time > 15:35). Shutting down.")
                 break

            prices = data_streamer.get_current_prices()
            
            nifty_ltp = prices['NIFTY']['ltp'] if prices['NIFTY'] else 0
            
            # Update last tick time if we have data
            if nifty_ltp > 0:
                last_tick_time = current_time
            
            # Timeout check (e.g., if no data for 60 seconds on a weekend/holiday)
            if (current_time - last_tick_time).total_seconds() > 60:
                if nifty_ltp == 0:
                    # If we never got a tick
                    logger.warning("⚠️ No data received for 60s. Market likely closed or connection dead.")
                    break
            
            ce_ltp = prices['CE']['ltp'] if prices['CE'] else 0
            pe_ltp = prices['PE']['ltp'] if prices['PE'] else 0
            
            # Check for Signals (Triggered by callback, but we handle execution here?)
            # Actually, on_candle_closed calls signal_scanner.on_candle_closed, which returns a signal?
            # Wait, the callback in streamer is: self.on_candle_closed_callback('NIFTY')
            # scanner.on_candle_closed returns 'BUY_CE' etc.
            # But the streamer doesn't capture the return value of the callback.
            
            # FIX: We need to actively check for signals if the scanner detected one, 
            # OR modify the architecture.
            # Phase 4 'live_trader_main.py' loop:
            # It waits for `data_streamer.new_candle_event`.
            # Since we are using a threaded websocket, the callback fires in a separate thread.
            
            # BETTER APPROACH FOR LIVE LOOP:
            # The Scanner runs logic on candle close.
            # But the Order Manager needs to execute on T+1 open (Tick level).
            # So we need to check for pending signals and update positions continuously here.
            
            # 1. Pass Market Data to Order Manager (for T+1 entry and Exits)
            # We need full candle data for execution (Open price). 
            # The streamer maintains `current_candles`.
            
            current_time = datetime.now()
            
            # Construct data objects for Order Manager
            # It expects dicts with 'open', 'atr', etc.
            # We might not have ATR real-time for options in the streamer unless calculated.
            # The Calculator has it.
            
            ce_indicators = indicator_calculator.get_option_indicators('CE')
            pe_indicators = indicator_calculator.get_option_indicators('PE')
            nifty_indicators = indicator_calculator.get_nifty_indicators()
            
            # Combine LTP with Indicators for Order Manager
            # (Order Manager uses 'open' from data to fill orders)
            
            # We need to ensure Order Manager gets the *current candle's* open for T+1 execution.
            # The `ce_indicators` are from the *last closed* candle.
            # `data_streamer.current_candles` has the *forming* candle.
            
            current_ce_data = data_streamer.current_candles['CE']
            current_pe_data = data_streamer.current_candles['PE']
            
            # If new candle just started, these might be None or fresh.
            if current_ce_data:
                # Inject ATR from previous closed candle (valid approximation for current)
                current_ce_data['atr'] = ce_indicators.get('atr', 0) 
                current_ce_data['strike_price'] = keys['ce'] # Store key/strike
            
            if current_pe_data:
                current_pe_data['atr'] = pe_indicators.get('atr', 0)
                current_pe_data['strike_price'] = keys['pe']

            # 2. Update Positions & Execute Pending Orders
            if nifty_ltp > 0 and current_ce_data and current_pe_data:
                closed_orders = order_manager.update_positions(
                    ce_price=ce_ltp,
                    pe_price=pe_ltp,
                    ce_high=prices['CE']['high'],
                    pe_high=prices['PE']['high'],
                    ce_data=current_ce_data, # For T+1 Entry (Open)
                    pe_data=current_pe_data,
                    nifty_indicators=nifty_indicators,
                    current_candle_time=current_time
                )
            
            # 3. Check for NEW Signals (from the Scanner which ran in the thread? No.)
            # The scanner needs to run. 
            # Problem: on_candle_closed_callback is in a thread.
            # We should let the callback handle the *detection* and store it in the Order Manager directly?
            # Yes, let's modify the connection.
            
            # ACTUALLY, the most robust way:
            # The callback `signal_scanner.on_candle_closed` returns the signal.
            # But `data_streamer` ignores the return.
            # Let's hook them up: 
            # We need a wrapper callback that catches the signal and sends it to order_manager.
            
            # I'll define it here locally or make a helper.
            
            # Dashboard
            sys.stdout.write(f"\r[LIVE MODE] {current_time.strftime('%H:%M:%S')} | NIFTY: {nifty_ltp:.2f} | CE: {ce_ltp:.2f} | PE: {pe_ltp:.2f} | Pos: {position_tracker.get_open_position_count()}")
            sys.stdout.flush()
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Manual Interruption. Shutting down...")
        data_streamer.disconnect()
        trade_logger.save_all(position_tracker)

if __name__ == "__main__":
    main()