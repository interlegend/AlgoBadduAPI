"""
LIVE TRADER MAIN
Main orchestrator for Phase 3 Live Paper Trading
Coordinates all components and manages trading session

Author: Commander Trader-Baddu
Powered by: King Gemini AI
"""

import os
import sys
import json
import logging
from datetime import datetime, time, timedelta
import time as time_module
import signal
import pandas as pd
import threading
import upstox_client
from dateutil.parser import parse

# Add parent directories to path
sys.path.append(r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-2')
sys.path.append(r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\UPSTOX-API')

# Import all components
from config_live import *
from atm_selector import ATMSelector
from indicator_calculator import IndicatorCalculator
from position_tracker import PositionTracker
from trade_logger import TradeLogger
from paper_order_manager import PaperOrderManager
from live_signal_scanner import LiveSignalScanner
from live_data_streamer import LiveDataStreamer
from strategy_v30 import StrategyV30

# --- Logging Setup ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f'live_trader_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        ),
        logging.StreamHandler() if CONSOLE_OUTPUT else logging.NullHandler()
    ]
)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)


class LiveTraderMain:
    def __init__(self):
        """Initialize Live Trader"""
        self.access_token = None
        self.running = False
        self.pulse_thread = None
        self.upstox_api = None
        
        # Components
        self.atm_selector = None
        self.indicator_calculator = None
        self.position_tracker = None
        self.trade_logger = None
        self.strategy = None
        self.paper_order_manager = None
        self.signal_scanner = None
        self.data_streamer = None
        
        self.atm_config = {}
        self.last_signal = "WAITING..."
        self.instrument_keys = {
            'nifty': NIFTY_INDEX_KEY,
            'ce': '',  # Placeholder, will be updated by atm_selector
            'pe': ''   # Placeholder, will be updated by atm_selector
        }
        
        logger.info("="*70)
        logger.info("🔥 TRADER-BADDU LIVE PAPER TRADER - PHASE 3")
        logger.info("="*70)
    
    def load_access_token(self):
        """Load Upstox access token from session file."""
        try:
            with open(SESSION_FILE, 'r') as f:
                session = json.load(f)
                self.access_token = session.get('access_token')
            if not self.access_token:
                raise ValueError("No access token found in session file.")
            
            # Configure API client
            configuration = upstox_client.Configuration()
            configuration.access_token = self.access_token
            self.upstox_api = upstox_client.ApiClient(configuration)
            logger.info("✅ Access token loaded and API client configured.")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load access token or configure API: {e}")
            logger.error("Please run the authentication script to generate a valid session file.")
            return False
    
    def initialize_components(self):
        """Initialize all trading components in order."""
        logger.info("\n" + "="*70 + "\n⚙️  INITIALIZING COMPONENTS\n" + "="*70)
        
        # 1. ATM Selector
        if MODE == "LIVE":
            logger.info("\n[1/8] Initializing ATM Selector...")
            self.atm_selector = ATMSelector(self.access_token)
            if not self.atm_selector.initialize_atm():
                logger.error("❌ ATM initialization failed!")
                return False
            self.atm_config = self.atm_selector.get_current_config()
            self.instrument_keys['ce'] = self.atm_config['ce_key']
            self.instrument_keys['pe'] = self.atm_config['pe_key']
            logger.info("✅ ATM Selector ready.")
        else: # MOCK MODE
            logger.info("\n[1/8] Skipping ATM Selector in MOCK mode. Using dummy config.")
            self.atm_config = {'strike': 26000, 'ce_key': 'DUMMY_CE', 'pe_key': 'DUMMY_PE'}
            self.instrument_keys['ce'] = self.atm_config['ce_key']
            self.instrument_keys['pe'] = self.atm_config['pe_key']
            logger.info("✅ ATM Selector bypassed.")

        # 2. Indicator Calculator
        logger.info("\n[2/8] Initializing Indicator Calculator...")
        self.indicator_calculator = IndicatorCalculator(buffer_size=CANDLE_BUFFER_SIZE)
        logger.info("✅ Indicator Calculator ready.")

        # 3. Position Tracker
        logger.info("\n[3/8] Initializing Position Tracker...")
        self.position_tracker = PositionTracker()
        logger.info("✅ Position Tracker ready.")

        # 4. Trade Logger
        logger.info("\n[4/8] Initializing Trade Logger...")
        self.trade_logger = TradeLogger(TRADE_LOG_DIR)
        logger.info("✅ Trade Logger ready.")

        # 5. Strategy V30
        logger.info("\n[5/8] Initializing Strategy V30...")
        self.strategy = StrategyV30()
        logger.info(f"   Strategy Version: {self.strategy.get_config()['version']}")
        logger.info("✅ Strategy V30 ready.")
        
        # 6. Paper Order Manager (depends on strategy, position_tracker, trade_logger)
        logger.info("\n[6/8] Initializing Paper Order Manager...")
        self.paper_order_manager = PaperOrderManager(
            self.strategy,
            self.position_tracker,
            self.trade_logger
        )
        logger.info("✅ Paper Order Manager ready.")

        # 7. Live Signal Scanner (depends on indicator_calculator)
        logger.info("\n[7/8] Initializing Live Signal Scanner...")
        self.signal_scanner = LiveSignalScanner(self.indicator_calculator)
        logger.info("✅ Signal Scanner ready.")

        # 8. Live Data Streamer (depends on access_token, instrument_keys, indicator_calculator)
        logger.info("\n[8/8] Initializing Live Data Streamer...")
        self.data_streamer = LiveDataStreamer(
            access_token=self.access_token,
            instrument_keys=self.instrument_keys,
            indicator_calculator=self.indicator_calculator,
            on_candle_closed_callback=self.on_candle_closed
        )
        logger.info("✅ Data Streamer ready.")
        
        logger.info("\n" + "="*70 + "\n✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY!\n" + "="*70)
        return True

    def warmup_indicators(self):
        """Fetch historical data to warm up indicators before live trading."""
        logger.info("\n" + "="*70 + "\n📊 WARMING UP INDICATORS\n" + "="*70)
        history_api = upstox_client.HistoryApi(self.upstox_api)
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d') # Fetch more days to be safe

        instruments_to_warmup = {
            "NIFTY": self.instrument_keys['nifty'],
            "CE": self.instrument_keys['ce'],
            "PE": self.instrument_keys['pe']
        }

        for name, key in instruments_to_warmup.items():
            try:
                logger.info(f"Fetching historical data for {name} ({key})...")
                response = history_api.get_historical_candle_data(key, '1minute', to_date, from_date)
                if response.status == 'success':
                    candles = response.data.candles
                    for c in reversed(candles[-INDICATOR_WARMUP_CANDLES:]):
                        # Format: [timestamp, open, high, low, close, volume, open_interest]
                        candle_data = {
                            'timestamp': parse(c[0]),
                            'open': c[1], 'high': c[2], 'low': c[3], 'close': c[4], 'volume': c[5]
                        }
                        self.indicator_calculator.add_candle(name, candle_data)
                    logger.info(f"✅ Warmed up {name} with {len(candles[-INDICATOR_WARMUP_CANDLES:])} candles.")
                else:
                    logger.error(f"❌ Failed to fetch historical data for {name}: {response.message}")
                    return False
            except Exception as e:
                logger.error(f"❌ Exception during {name} warmup: {e}", exc_info=True)
                return False
        return True

    def on_candle_closed(self, candle_type):
        """Callback triggered when a 5-minute candle closes. Main heartbeat."""
        if candle_type != 'NIFTY':
            return
        
        logger.info(f"--- 5-Min NIFTY Candle Closed @ {datetime.now().strftime('%H:%M:%S')} ---")
        
        # 1. Calculate all indicators first
        self.indicator_calculator.calculate_nifty_indicators()
        self.indicator_calculator.calculate_option_indicators('CE')
        self.indicator_calculator.calculate_option_indicators('PE')

        # 2. Scan for a new signal using the fresh indicator data
        signal = self.signal_scanner.on_candle_closed(candle_type)
        self.last_signal = signal if signal else "WAITING..."
        
        # 3. Display the full dashboard with the new candle, indicators, and signal status
        self.display_dashboard()
        
        # 4. Handle the signal (if any)
        if signal:
            self.handle_signal(signal)
        
        # 5. Update any open positions with the latest data
        self.update_positions()

    
    def handle_signal(self, signal):
        """Handle an entry signal by placing a paper order."""
        # ... (logic remains the same)
    
    def update_positions(self):
        """Update all open positions based on the latest market data."""
        # ... (logic remains the same)

    def display_dashboard(self):
        """Display the Phase 4 'Deep History' Matrix Simulation dashboard."""
        os.system('cls' if os.name == 'nt' else 'clear')

        # --- Get Live & Historical Data ---
        prices = self.data_streamer.get_current_prices()
        spot_price = prices.get('NIFTY', {}).get('ltp', 0.0)
        atm_strike = self.atm_config.get('strike', 'N/A')
        sim_time = self.indicator_calculator.get_nifty_indicators().get('timestamp', datetime.now())

        nifty_history = self.indicator_calculator.get_nifty_data().tail(3)
        ce_history = self.indicator_calculator.get_option_data('CE').tail(3)
        pe_history = self.indicator_calculator.get_option_data('PE').tail(3)

        # --- Build Dashboard ---
        print("="*78)
        print("=================== 🧪 PHASE 4: MATRIX SIMULATION (V30) 🧪 ===================")
        print("="*78)
        
        if spot_price > 0:
            print(f"⏰ SIMULATED TIME: {sim_time.strftime('%Y-%m-%d %H:%M')} | 💰 MOCK SPOT: {spot_price:.2f} | 🎯 MOCK ATM: {atm_strike}")
        else:
            print(f"⏰ SIMULATED TIME: {sim_time.strftime('%Y-%m-%d %H:%M')} | 💰 MOCK SPOT: Connecting... | 🎯 MOCK ATM: {atm_strike}")

        print("------------------------------------------------------------------------------")
        print("🕯️  RECENT MARKET HISTORY (Last 3 Closed Candles):")
        
        labels = ['   [NIFTY] [T-10min]', '   [NIFTY] [T-05min]', '   [NIFTY] [CURRENT]']
        
        if nifty_history.empty or len(nifty_history) < 3:
            print("   Not enough historical data to display.")
        else:
            for i in range(len(nifty_history)):
                nifty_candle = nifty_history.iloc[i]
                ce_close = ce_history.iloc[i]['close'] if i < len(ce_history) else '----'
                pe_close = pe_history.iloc[i]['close'] if i < len(pe_history) else '----'
                
                ce_str = f"{ce_close:.2f}" if isinstance(ce_close, (int, float)) else ce_close
                pe_str = f"{pe_close:.2f}" if isinstance(pe_close, (int, float)) else pe_close

                label = labels[i]
                if i == len(nifty_history) - 1:
                    label += " (SIGNAL CANDLE)"
                
                print(f"{label} O:{nifty_candle['open']:.2f} C:{nifty_candle['close']:.2f} | [CE] C:[{ce_str.rjust(7)}] | [PE] C:[{pe_str.rjust(7)}]")

        print("------------------------------------------------------------------------------")
        
        indicators = self.indicator_calculator.get_nifty_indicators()
        if not indicators:
            print("📊 INDICATORS: Not yet calculated.")
        else:
            ema = indicators.get('ema21', 0.0)
            vi_plus = indicators.get('vi_plus', 0.0)
            vi_minus = indicators.get('vi_minus', 0.0)
            print(f"📊 INDICATORS: EMA(21): {ema:.2f} | Vortex: {vi_plus:.4f} / {vi_minus:.4f}")
        
        # Update signal status with drawdown info
        open_pos = self.position_tracker.get_all_open_positions()
        if open_pos:
            pnl = open_pos[0].get('pnl', 0.0)
            max_drawdown = open_pos[0].get('max_drawdown', 0.0)
            status_msg = f"IN TRADE ({open_pos[0]['type']}) | P&L: ₹{pnl:.2f} | Max Drawdown: ₹{max_drawdown:.2f}"
            print(f"🚥 SIGNAL STATUS: {status_msg}")
        else:
            print(f"🚥 SIGNAL STATUS: {self.last_signal}")
            
        print("==============================================================================")

    def start_trading_session(self):
        """Starts the main trading loop in either LIVE or MOCK mode."""
        logger.info(f"\n{'='*70}\n🚀 STARTING TRADING SESSION ({MODE} MODE)\n{'='*70}")
        
        # Start the data streamer (either mock or live)
        if not self.data_streamer.start():
            logger.error("❌ Data streamer failed to start. Aborting.")
            self.shutdown()
            return
            
        self.running = True
        
        # Main execution loop (HEARTBEAT)
        logger.info("✅ Entering main execution loop. Waiting for market data...")
        
        try:
            # In MOCK mode, the streamer controls the loop timing.
            # In LIVE mode, this loop keeps the main thread alive.
            while self.running and self.data_streamer.running:
                if MODE == 'LIVE':
                    spot = self.data_streamer.get_current_prices().get('NIFTY', {}).get('ltp', 0.0)
                    pulse_msg = f"⏳ Waiting for 5-min candle close... | Signal: {self.last_signal} | NIFTY LTP: {spot:.2f}"
                    print(pulse_msg, end='\r')
                
                # The mock streamer has its own delay, so a short sleep here is fine
                time_module.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\n⌨️ KeyboardInterrupt detected. Initiating shutdown...")
        finally:
            self.shutdown()
        
        logger.info("Exited main trading loop.")

    def shutdown(self):
        """Gracefully shut down the trading session and all components."""
        if not self.running:
            return
        logger.info("\n" + "="*70 + "\n🔌 SHUTTING DOWN TRADING SESSION\n" + "="*70)
        self.running = False
        if self.data_streamer:
            self.data_streamer.disconnect()
        
        if self.pulse_thread and self.pulse_thread.is_alive():
            self.pulse_thread.join(timeout=1)
        
        if self.position_tracker.get_open_position_count() > 0:
            logger.info("⚠️ Closing all open positions...")
            prices = self.data_streamer.get_current_prices()
            ce_price = prices.get('CE', {}).get('ltp', 0)
            pe_price = prices.get('PE', {}).get('ltp', 0)
            self.paper_order_manager.force_close_all_positions(ce_price, pe_price)
        
        logger.info("\n💾 Saving final logs...")
        self.trade_logger.save_all(self.position_tracker)
        
        logger.info("\n" + "="*70 + "\n✅ SHUTDOWN COMPLETE!\n" + "="*70)

    def run(self):
        """Main entry point to run the trader."""
        # In MOCK mode, we don't need a real access token or to warm up indicators from live data
        if MODE == "MOCK":
            # A dummy token is needed for component initialization, but it won't be used for API calls
            self.access_token = "MOCK_TOKEN"
            if self.initialize_components():
                self.start_trading_session()
        else: # LIVE mode
            try:
                if self.load_access_token() and self.initialize_components() and self.warmup_indicators():
                    self.start_trading_session()
            except Exception as e:
                logger.error(f"\n💥 A FATAL ERROR occurred: {e}", exc_info=True)
                self.shutdown()


def main():
    """Main function to run the application."""
    title = "PHASE 4: MATRIX SIMULATION (V30)" if MODE == "MOCK" else "Phase 3: Real-Time Signal Detection"
    print("\n" + "🧪"*35 if MODE == "MOCK" else "🔥"*35)
    print(f"   TRADER-BADDU - {title}")
    print("🧪"*35 if MODE == "MOCK" else "🔥"*35 + "\n")
    
    trader = LiveTraderMain()
    
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutdown signal received! Initiating graceful shutdown...")
        if trader:
            trader.running = False
            if trader.data_streamer:
                trader.data_streamer.running = False # Ensure streamer loop also exits
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    trader.run()
    
    print("\n" + "="*70)
    print("✅ TRADER-BADDU SESSION ENDED")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()

    