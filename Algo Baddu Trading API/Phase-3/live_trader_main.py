"""
LIVE TRADER MAIN - PHASE 3 (DEPLOYMENT) - UI UPGRADE
Integrates Real Strategy V30 + Live Upstox Data + Warm-Up Logic + DASHBOARD
"""

import time
import logging
import json
import sys
import os
from datetime import datetime
import pandas as pd

# Force UTF-8 encoding for Windows Console (Essential for emojis)
sys.stdout.reconfigure(encoding='utf-8')

# === IMPORT CORE MODULES ===
from config_live import UPSTOX_ACCESS_TOKEN, PROJECT_ROOT
from live_data_streamer import LiveDataStreamer
from indicator_calculator import IndicatorCalculator
from live_signal_scanner import LiveSignalScanner
from paper_order_manager import PaperOrderManager
from trade_logger import TradeLogger
from position_tracker import PositionTracker
from atm_selector import ATMSelector 

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

# Global State for UI
ui_state = {
    "last_signal": "WAITING...",
    "atm_strike": "N/A"
}

def load_instrument_keys():
    """
    Dynamic ATM Selector for Live Trading.
    Returns: dict with keys and sets the global atm_strike
    """
    NIFTY_KEY = "NSE_INDEX|Nifty 50"
    ce_key = None
    pe_key = None
    
    # Fetch initial Spot to determine ATM
    import requests
    url = "https://api.upstox.com/v2/market-quote/ltp?instrument_key=NSE_INDEX|Nifty 50"
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            nifty_ltp = data['data']['NSE_INDEX:Nifty 50']['last_price']
            logger.info(f"✅ Current NIFTY Spot: {nifty_ltp}")
            
            # Select ATM keys
            selector = ATMSelector(UPSTOX_ACCESS_TOKEN)
            atm_strike, ce_key, pe_key = selector.get_atm_keys(nifty_ltp)
            
            # UPDATE GLOBAL STATE
            ui_state["atm_strike"] = atm_strike
            
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

def display_dashboard(data_streamer, indicator_calculator, paper_order_manager):
    """
    Prints the verified Phase 4 Dashboard with Live Data.
    """
    prices = data_streamer.get_current_prices()
    
    # FIX: Safely handle None values for NIFTY (Initial State)
    nifty_data = prices.get('NIFTY') or {} 
    spot_price = nifty_data.get('ltp', 0.0)
    
    nifty_indicators = indicator_calculator.get_nifty_indicators()

    # Fallback: If spot is 0 (start of day/warmup), use last known Close from indicators
    if spot_price == 0.0 and nifty_indicators:
         spot_price = nifty_indicators.get('close', 0.0)

    atm_strike = ui_state["atm_strike"]
    sim_time = nifty_indicators.get('timestamp') # This is the time of the CLOSED candle

    nifty_history = indicator_calculator.get_nifty_data().tail(3)
    ce_history = indicator_calculator.get_option_data('CE').tail(3)
    pe_history = indicator_calculator.get_option_data('PE').tail(3)

    print("\n" + "="*78)
    print(f"=================== ⚡ PHASE 3: LIVE BATTLEFIELD (V30) ⚡ ===================")
    print("="*78)
    
    if pd.notna(sim_time):
        print(f"⏰ CANDLE: {sim_time.strftime('%Y-%m-%d %H:%M')} | 💰 SPOT: {spot_price:.2f} | 🎯 ATM: {atm_strike}")
    else:
        print(f"⏰ CANDLE: Initializing... | 💰 SPOT: {spot_price:.2f} | 🎯 ATM: {atm_strike}")

    print("-----------------------------------------------------------------------------")
    print("🕯️  RECENT MARKET HISTORY (Synced):")
    
    if nifty_history.empty:
        print("   Waiting for candle data...")
    else:
        labels = ['   [NIFTY] [T-10min]', '   [NIFTY] [T-05min]', '   [NIFTY] [CURRENT]']
        if len(nifty_history) < 3:
            labels = labels[-len(nifty_history):]

        for i in range(len(nifty_history)):
            nifty_candle = nifty_history.iloc[i]
            
            # Safely get Option Closes
            ce_ltp = '----'
            if i < len(ce_history) and not ce_history.empty:
                 ce_ltp = f"{ce_history.iloc[i]['close']:.2f}"
            
            pe_ltp = '----'
            if i < len(pe_history) and not pe_history.empty:
                 pe_ltp = f"{pe_history.iloc[i]['close']:.2f}"
            
            label = labels[i]
            if i == len(nifty_history) - 1:
                label += " (SIGNAL CANDLE)"

            print(f"{label} O:{nifty_candle['open']:.2f} C:{nifty_candle['close']:.2f} | [CE] LTP: {ce_ltp.rjust(7)} | [PE] LTP: {pe_ltp.rjust(7)}")

    print("-----------------------------------------------------------------------------")
    
    if not nifty_indicators:
        print("📊 INDICATORS: Not yet calculated.")
    else:
        # Hardcoded params matching StrategyV30
        ema_period = 21 
        vi_period = 34 # V30 uses 34
        ema_key = f'ema{ema_period}'
        vi_plus_key = f'vi_plus_{vi_period}'
        vi_minus_key = f'vi_minus_{vi_period}'

        ema_val = nifty_indicators.get(ema_key, 0.0)
        vi_plus = nifty_indicators.get(vi_plus_key, 0.0)
        vi_minus = nifty_indicators.get(vi_minus_key, 0.0)

        print(f"📊 INDICATORS: EMA({ema_period}): {ema_val:.2f} | Vortex({vi_period}): {vi_plus:.4f} / {vi_minus:.4f}")
    
    print(f"🚥 SIGNAL CHECK: {ui_state['last_signal']}")
    
    # Display pending T+1 signal if exists
    if paper_order_manager.pending_signal:
        print(f"⏳ PENDING T+1 ORDER: {paper_order_manager.pending_signal}")
    
    print("=============================================================================\n")

def main():
    print("="*70)
    print("🚀 TRADER-BADDU LIVE TRADER (PHASE 3) - SYSTEM START")
    print("="*70)
    
    # 1. Initialize Components
    trade_logger = TradeLogger(os.path.join(PROJECT_ROOT, "trade_logs"))
    position_tracker = PositionTracker()
    
    # Initialize Strategy FIRST to get parameters
    from strategy_v30 import StrategyV30
    strategy = StrategyV30()
    
    # Pass strategy config to Calculator so it uses correct VI Period (34)
    indicator_calculator = IndicatorCalculator(
        buffer_size=500, 
        strategy_params=strategy.get_config()
    )
    
    signal_scanner = LiveSignalScanner(indicator_calculator, position_tracker)
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
        # Only process NIFTY close for signals
        if candle_type != 'NIFTY':
            return

        # 1. Detect Signal
        signal = signal_scanner.on_candle_closed(candle_type)
        ui_state["last_signal"] = signal if signal else "WAITING..."
        
        # 2. Route to Order Manager if Valid
        if signal:
            nifty_data = indicator_calculator.get_nifty_indicators()
            signal_time = nifty_data.get('timestamp', datetime.now())
            logger.info(f"🔗 BRIDGE: Routing {signal} @ {signal_time} to Order Manager")
            order_manager.on_signal_detected(signal, signal_time)
            
        # 3. PRINT DASHBOARD (Triggers exactly when candle closes, like Phase 4)
        display_dashboard(data_streamer, indicator_calculator, order_manager)

    # 3. Initialize Data Streamer with Warm-Up
    data_streamer = LiveDataStreamer(
        access_token=UPSTOX_ACCESS_TOKEN,
        instrument_keys=keys,
        indicator_calculator=indicator_calculator,
        on_candle_closed_callback=signal_handler_callback
    )
    
    # 4. EXECUTE WARM-UP
    print("\n⏳ EXECUTING WARM-UP SEQUENCE (Getting the Time Machine ready)...")
    data_streamer.initialize_warmup(days=5)
    
    # Force calculation on historical data and Show Initial Dashboard
    logger.info("🔄 Calculating indicators on Warm-Up data...")
    indicator_calculator.calculate_nifty_indicators()
    indicator_calculator.calculate_option_indicators('CE')
    indicator_calculator.calculate_option_indicators('PE')
    print("\n✨ WARM-UP COMPLETE. INITIAL DASHBOARD:")
    display_dashboard(data_streamer, indicator_calculator, order_manager)
    
    # 5. START LIVE STREAMING
    print("\n🔌 CONNECTING TO LIVE WEBSOCKET...")
    if not data_streamer.start_websocket():
        logger.error("❌ Failed to connect to WebSocket. Exiting.")
        return

    logger.info("✅ SYSTEM LIVE. WAITING FOR TICKS...")
    
    # Allow a moment for connection to stabilize
    time.sleep(2)
    
    last_tick_time = datetime.now()
    last_debug_time = datetime.now()
    
    try:
        while True:
            # === THE LIVE HEARTBEAT ===
            current_time = datetime.now()
            
            # Market Hours Check (Simple Guard)
            if current_time.hour >= 15 and current_time.minute >= 35:
                 logger.info("🌙 Market Closed (Time > 15:35). Shutting down.")
                 break

            # --- 1. DEBUG HEARTBEAT (Every 60s) ---
            if (current_time - last_debug_time).total_seconds() >= 60:
                logger.info(f"💓 SYSTEM HEARTBEAT | Connected: {data_streamer.is_connected} | Last Data: {last_tick_time.strftime('%H:%M:%S')}")
                last_debug_time = current_time

            # --- 2. FETCH LATEST DATA (Buffered by Streamer) ---
            prices = data_streamer.get_current_prices()
            nifty_ltp = prices['NIFTY']['ltp'] if prices['NIFTY'] else 0
            
            if nifty_ltp > 0:
                last_tick_time = current_time
            
            # --- 3. CONNECTION GUARD ---
            # If no data for 60s, warn but don't kill (allow reconnect)
            if (current_time - last_tick_time).total_seconds() > 60:
                if not data_streamer.is_connected:
                    sys.stdout.write("\r⚠️ WebSocket Disconnected! Waiting for reconnect...      ")
                    sys.stdout.flush()
                    time.sleep(1)
                    continue
                elif nifty_ltp == 0:
                     # Connected but no NIFTY data yet?
                     pass
            
            # Fallback Logic for 0.00 Display (NIFTY)
            display_ltp = nifty_ltp
            ltp_suffix = ""
            if display_ltp == 0:
                nifty_ind = indicator_calculator.get_nifty_indicators()
                if nifty_ind and 'close' in nifty_ind:
                    display_ltp = nifty_ind['close']
                    ltp_suffix = "(LC)"

            ce_ltp = prices['CE']['ltp'] if prices['CE'] else 0
            pe_ltp = prices['PE']['ltp'] if prices['PE'] else 0
            
            # Fallback Logic for Options (CE/PE)
            ce_suffix = ""
            if ce_ltp == 0:
                ce_ind = indicator_calculator.get_option_indicators('CE')
                if ce_ind and 'close' in ce_ind:
                    ce_ltp = ce_ind['close']
                    ce_suffix = "(LC)"

            pe_suffix = ""
            if pe_ltp == 0:
                pe_ind = indicator_calculator.get_option_indicators('PE')
                if pe_ind and 'close' in pe_ind:
                    pe_ltp = pe_ind['close']
                    pe_suffix = "(LC)"
            
            # Update Positions continuously (Tick-by-Tick P&L)
            current_ce_data = data_streamer.current_candles['CE']
            current_pe_data = data_streamer.current_candles['PE']
            
            if nifty_ltp > 0 and current_ce_data and current_pe_data:
                # Inject latest ATR if missing
                if 'atr' not in current_ce_data:
                    current_ce_data['atr'] = indicator_calculator.get_option_indicators('CE').get('atr', 0)
                if 'atr' not in current_pe_data:
                    current_pe_data['atr'] = indicator_calculator.get_option_indicators('PE').get('atr', 0)
                
                order_manager.update_positions(
                    ce_price=ce_ltp,
                    pe_price=pe_ltp,
                    ce_high=prices['CE']['high'],
                    pe_high=prices['PE']['high'],
                    ce_data=current_ce_data,
                    pe_data=current_pe_data,
                    nifty_indicators=indicator_calculator.get_nifty_indicators(),
                    current_candle_time=current_time
                )
            
            # --- VISUAL PULSE (Updates every 1 sec) ---
            # Attempt to calculate LIVE indicators on the forming candle
            live_nifty_candle = data_streamer.current_candles.get('NIFTY')
            nifty_ind_live = {}
            
            if live_nifty_candle:
                # Calculate on the fly
                nifty_ind_live = indicator_calculator.calculate_live_indicators('NIFTY', live_nifty_candle)
            
            # Fallback to last closed candle indicators if live ones aren't ready
            if not nifty_ind_live:
                nifty_ind_live = indicator_calculator.get_nifty_indicators()

            # Extract values (Strategy V30 uses EMA21 and VI34)
            ema_val = nifty_ind_live.get(f'ema21', 0)
            vi_plus = nifty_ind_live.get(f'vi_plus_34', 0)
            vi_minus = nifty_ind_live.get(f'vi_minus_34', 0)
            
            pos_count = position_tracker.get_open_position_count()
            
            # Clean & sleek status line (Aligned)
            sys.stdout.write("\r" + " "*120 + "\r") # Erase previous
            
            # Status Icon
            status_icon = "🟢" if ui_state['last_signal'] != "WAITING..." else "📡"
            
            # Dynamic signal text
            sig_text = f"SIGNAL: {ui_state['last_signal']}"
            
            msg = (f"{status_icon} [LIVE] {current_time.strftime('%H:%M:%S')} | "
                   f"NIFTY: {display_ltp:>8.2f} {ltp_suffix:<4} | "
                   f"CE: {ce_ltp:>6.2f} {ce_suffix:<4} | PE: {pe_ltp:>6.2f} {pe_suffix:<4} | "
                   f"EMA: {ema_val:>8.1f} | VI: {vi_plus:>5.3f}/{vi_minus:<5.3f} | "
                   f"{sig_text}")
            
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Manual Interruption. Shutting down...")
        data_streamer.disconnect()
        trade_logger.save_all(position_tracker)

if __name__ == "__main__":
    main()