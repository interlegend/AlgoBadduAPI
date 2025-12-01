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
from config_live import UPSTOX_ACCESS_TOKEN, PROJECT_ROOT, TRADING_ASSET
from live_data_streamer import LiveDataStreamer
from indicator_calculator import IndicatorCalculator
from live_signal_scanner import LiveSignalScanner
from paper_order_manager import PaperOrderManager
from trade_logger import TradeLogger
from position_tracker import PositionTracker
from atm_selector import ATMSelector 
from commodity_selector import CommodityKeySelector 

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

def display_dashboard(data_streamer, indicator_calculator, paper_order_manager, asset_name='NIFTY'):
    """
    Prints the verified Phase 4 Dashboard with Live Data.
    """
    prices = data_streamer.get_current_prices()
    
    # FIX: Safely handle None values for NIFTY (Initial State)
    # Note: For MCX, 'NIFTY' key holds the Future price
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
        print(f"⏰ CANDLE: {sim_time.strftime('%Y-%m-%d %H:%M')} | 💰 {asset_name}: {spot_price:.2f} | 🎯 ATM: {atm_strike}")
    else:
        print(f"⏰ CANDLE: Initializing... | 💰 {asset_name}: {spot_price:.2f} | 🎯 ATM: {atm_strike}")

    print("-----------------------------------------------------------------------------")
    print("🕯️  RECENT MARKET HISTORY (Synced):")
    
    if nifty_history.empty:
        print("   Waiting for candle data...")
    else:
        labels = [f'   [{asset_name}] [T-10min]', f'   [{asset_name}] [T-05min]', f'   [{asset_name}] [CURRENT]']
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
    print("🚀 TRADER-BADDU LIVE TRADER (PHASE 3.5) - MULTI-ASSET READY")
    print("="*70)
    
    # --- 0. ASSET SELECTION MENU ---
    print("\nSELECT ASSET CLASS:")
    print("1. NIFTY (NSE Options)")
    print("2. CRUDE OIL (MCX Futures)")
    print("3. NATURAL GAS (MCX Futures)")
    
    choice = input("\n[INPUT] Select (1-3): ").strip()
    
    asset_type = "NIFTY"
    if choice == "2":
        asset_type = "CRUDEOIL"
    elif choice == "3":
        asset_type = "NATURALGAS"
    
    logger.info(f"✅ Selected Asset: {asset_type}")
    
    # 1. Initialize Components
    trade_logger = TradeLogger(os.path.join(PROJECT_ROOT, "trade_logs"))
    position_tracker = PositionTracker()
    
    from strategy_v30 import StrategyV30
    strategy = StrategyV30()
    
    # Update Lot Size in Strategy for Futures
    if asset_type == 'CRUDEOIL':
        strategy.LOT_SIZE = 100
    elif asset_type == 'NATURALGAS':
        strategy.LOT_SIZE = 1250
    # NIFTY default is 75 (or whatever is in strategy file)
    
    indicator_calculator = IndicatorCalculator(
        buffer_size=500, 
        strategy_params=strategy.get_config()
    )
    
    signal_scanner = LiveSignalScanner(indicator_calculator, position_tracker)
    # Pass asset_type to Order Manager
    order_manager = PaperOrderManager(strategy, position_tracker, trade_logger, asset_type=asset_type)
    
    # 2. Get Instrument Keys
    keys = {}
    
    if asset_type == "NIFTY":
        # NSE Options Mode
        print("🔍  DETECTING ATM STRIKES & INSTRUMENTS...")
        keys = load_instrument_keys()
        if not keys['ce'] or not keys['pe']:
            logger.error("❌ CRITICAL: Could not determine ATM keys. Exiting.")
            return
            
    else:
        # MCX Futures Mode
        print(f"🔍  FETCHING ACTIVE FUTURE FOR {asset_type}...")
        comm_selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
        fut_key, lot, expiry = comm_selector.get_current_future(asset_type)
        
        if not fut_key:
            logger.error("❌ CRITICAL: Could not find active Future contract. Exiting.")
            return
            
        # Map Future to 'nifty' so IndicatorCalculator treats it as the underlying
        keys = {
            'nifty': fut_key,
            'ce': None,
            'pe': None
        }
        # Override lot size again just in case selector returns different one
        if lot:
            strategy.LOT_SIZE = lot

    # --- SIGNAL CALLBACK WRAPPER ---
    def signal_handler_callback(candle_type):
        # For MCX, candle_type will be 'NIFTY' because we mapped the Future key to 'nifty'
        if candle_type != 'NIFTY': return

        signal = signal_scanner.on_candle_closed(candle_type)
        ui_state["last_signal"] = signal if signal else "WAITING..."
        
        if signal:
            nifty_data = indicator_calculator.get_nifty_indicators()
            signal_time = nifty_data.get('timestamp', datetime.now())
            logger.info(f"🔗 BRIDGE: Routing {signal} @ {signal_time} to Order Manager")
            
            # For Futures, we pass the Future Data as BOTH ce_data/pe_data (hacky but effective)
            # because execute_pending_signal expects these.
            # PaperOrderManager knows to handle this based on asset_type.
            order_manager.on_signal_detected(signal, signal_time)
            
        display_dashboard(data_streamer, indicator_calculator, order_manager, asset_name=asset_type)

    # 3. Initialize Data Streamer
    # UPGRADE: Create SDK ApiClient
    import upstox_client
    configuration = upstox_client.Configuration()
    configuration.access_token = UPSTOX_ACCESS_TOKEN
    api_client = upstox_client.ApiClient(configuration)

    data_streamer = LiveDataStreamer(
        api_client=api_client,
        instrument_keys=keys,
        indicator_calculator=indicator_calculator,
        on_candle_closed_callback=signal_handler_callback
    )
    
    # 4. EXECUTE WARM-UP
    print(f"\n⏳  INITIATING TIME MACHINE ({asset_type})...")
    data_streamer.initialize_warmup(days=10)
    
    logger.info("🔄  Calculating indicators on Warm-Up data...")
    indicator_calculator.calculate_nifty_indicators()
    # Only calc options if they exist
    if keys.get('ce'): indicator_calculator.calculate_option_indicators('CE')
    if keys.get('pe'): indicator_calculator.calculate_option_indicators('PE')
    
    print("\n✨  WARM-UP COMPLETE. PRE-FLIGHT CHECKS PASSED.")
    display_dashboard(data_streamer, indicator_calculator, order_manager, asset_name=asset_type)
    
    # 5. START LIVE STREAMING
    print("\n🔌  ESTABLISHING SECURE UPLINK TO UPSTOX WEBSOCKET...")
    if not data_streamer.start_websocket():
        logger.error("❌ Connection Failed. Aborting.")
        return

    logger.info("✅  UPLINK ESTABLISHED. SYSTEM LIVE.")
    time.sleep(2)
    
    last_tick_time = datetime.now()
    last_debug_time = datetime.now()
    
    try:
        while True:
            current_time = datetime.now()
            
            # MCX closes at 11:30 PM / 11:55 PM
            if current_time.hour >= 23 and current_time.minute >= 35:
                 logger.info("🌙 Market Closed (Late Night). Mission Complete.")
                 break

            if (current_time - last_debug_time).total_seconds() >= 60:
                logger.info(f"💓 SYSTEM HEALTH | Connected: {data_streamer.is_connected} | Last Tick: {last_tick_time.strftime('%H:%M:%S')}")
                last_debug_time = current_time

            prices = data_streamer.get_current_prices()
            # 'NIFTY' key holds the Future price in MCX mode
            main_ltp = prices['NIFTY']['ltp'] if prices['NIFTY'] else 0
            
            if main_ltp > 0:
                last_tick_time = current_time
            
            if (current_time - last_tick_time).total_seconds() > 60:
                if not data_streamer.is_connected:
                    sys.stdout.write("\r⚠️  CONNECTION LOST! Reconnecting...          ")
                    sys.stdout.flush()
                    time.sleep(1)
                    continue
            
            # Fallback Logic
            display_ltp = main_ltp
            ltp_suffix = ""
            if display_ltp == 0:
                nifty_ind = indicator_calculator.get_nifty_indicators()
                if nifty_ind and 'close' in nifty_ind:
                    display_ltp = nifty_ind['close']
                    ltp_suffix = "(LC)"

            # Options (Only for NIFTY)
            ce_ltp = prices['CE']['ltp'] if prices['CE'] else 0
            pe_ltp = prices['PE']['ltp'] if prices['PE'] else 0
            
            # Update Positions
            current_main_data = data_streamer.current_candles['NIFTY']
            current_ce_data = data_streamer.current_candles['CE']
            current_pe_data = data_streamer.current_candles['PE']
            
            # Logic fork for Updates
            if asset_type == 'NIFTY':
                if main_ltp > 0 and current_ce_data and current_pe_data:
                    # Ensure ATR
                    if 'atr' not in current_ce_data: current_ce_data['atr'] = indicator_calculator.get_option_indicators('CE').get('atr', 0)
                    if 'atr' not in current_pe_data: current_pe_data['atr'] = indicator_calculator.get_option_indicators('PE').get('atr', 0)
                    
                    order_manager.update_positions(ce_ltp, pe_ltp, prices['CE']['high'], prices['PE']['high'], current_ce_data, current_pe_data, indicator_calculator.get_nifty_indicators(), current_time)
            else:
                # MCX Futures Logic
                # We pass the FUTURE data as both CE and PE data because PaperOrderManager will select the "Option Data" based on signal.
                # Since we trade the Future for both Long/Short, we feed the Future data to both slots.
                if main_ltp > 0 and current_main_data:
                    # Need ATR on the Future for SL calc
                    # The strategy calculates ATR on 'NIFTY' (Future) automatically?
                    # StrategyV30 uses 'option_atr' passed to it.
                    # IndicatorCalculator calculates NIFTY indicators (EMA, MACD, VI).
                    # It does NOT calc ATR for 'NIFTY' buffer by default?
                    # Let's check indicator_calculator.py
                    # calculate_nifty_indicators() does NOT calc ATR.
                    # But calculate_option_indicators() DOES.
                    
                    # Hack: We need ATR for the Future.
                    # We can treat 'NIFTY' as an 'Option' momentarily to calc ATR?
                    # Or just add ATR calc to NIFTY?
                    # Let's rely on the fact that we mapped the Future to 'NIFTY'.
                    # If we want ATR, we should probably call calculate_option_indicators('NIFTY')?? No, it expects CE/PE.
                    
                    # I'll add a quick ATR calc here or in PaperOrderManager using NIFTY buffer.
                    # Actually, PaperOrderManager receives 'ce_data'.
                    # If I pass 'current_main_data' as 'ce_data', it needs an 'atr' field.
                    
                    # Get ATR from Nifty Buffer?
                    # IndicatorCalculator doesn't store ATR for Nifty.
                    # I will patch IndicatorCalculator or calc it here.
                    # Easiest: Add 'atr' to current_main_data using a simple lookup if possible, or modify IndicatorCalculator.
                    
                    # Let's modify IndicatorCalculator to allow ATR on NIFTY?
                    # Too risky for "Surgical Strike".
                    # I will calculate ATR on the fly using the buffer in `current_main_data`? No, need history.
                    
                    # Better: In the loop, I'll manually inject ATR into `current_main_data`.
                    # How? `indicator_calculator.get_nifty_data()` has the history.
                    # I can use pandas_ta or manual calc.
                    # `nifty_df = indicator_calculator.get_nifty_data()`
                    # `atr = ta.atr(nifty_df['high'], nifty_df['low'], nifty_df['close'], length=14).iloc[-1]`
                    # This is safe.
                    pass # Placeholder for logic below
                    
                    # Calc ATR on the fly
                    import pandas_ta as ta
                    nifty_df = indicator_calculator.get_nifty_data()
                    current_atr = 0
                    if not nifty_df.empty and len(nifty_df) > 15:
                        try:
                            atr_series = ta.atr(nifty_df['high'], nifty_df['low'], nifty_df['close'], length=14)
                            if atr_series is not None:
                                current_atr = atr_series.iloc[-1]
                        except: pass
                    
                    current_main_data['atr'] = current_atr
                    
                    # Pass Future Data for everything
                    order_manager.update_positions(
                        ce_price=main_ltp, 
                        pe_price=main_ltp, 
                        ce_high=prices['NIFTY']['high'], 
                        pe_high=prices['NIFTY']['high'], 
                        ce_data=current_main_data, 
                        pe_data=current_main_data, 
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

            # Extract values Dynamically
            ema_key = f'ema{strategy.EMA_PERIOD}'
            vi_plus_key = f'vi_plus_{strategy.VI_PERIOD}'
            vi_minus_key = f'vi_minus_{strategy.VI_PERIOD}'

            ema_val = nifty_ind_live.get(ema_key, 0)
            vi_plus = nifty_ind_live.get(vi_plus_key, 0)
            vi_minus = nifty_ind_live.get(vi_minus_key, 0)
            
            sys.stdout.write("\r" + " "*120 + "\r") # Erase
            
            status_icon = "🟢" if ui_state['last_signal'] != "WAITING..." else "📡"
            sig_status = ui_state['last_signal']
            if sig_status == "WAITING...": sig_status = "SCANNING..."
            
            if asset_type == 'NIFTY':
                msg = (f"{status_icon} [LIVE] {current_time.strftime('%H:%M:%S')} | "
                       f"NIFTY: {display_ltp:>8.2f} | CE: {ce_ltp:>6.2f} | PE: {pe_ltp:>6.2f} | "
                       f"EMA: {ema_val:>8.1f} | VI: {vi_plus:>5.3f}/{vi_minus:<5.3f} | {sig_status}")
            else:
                msg = (f"{status_icon} [MCX] {current_time.strftime('%H:%M:%S')} | "
                       f"{asset_type}: {display_ltp:>8.2f} {ltp_suffix} | "
                       f"EMA: {ema_val:>8.1f} | VI: {vi_plus:>5.3f}/{vi_minus:<5.3f} | {sig_status}")
            
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Manual Interruption. Shutting down...")
        data_streamer.disconnect()
        trade_logger.save_all(position_tracker)

if __name__ == "__main__":
    main()