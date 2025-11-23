"""
LIVE TRADER MAIN - FIXED VERSION
Main orchestrator for Phase 4 Simulation
IMPLEMENTS: T+1 Execution, Full Candle Data, Proper Warmup
"""

import os
import sys
import json
import logging
from datetime import datetime, time
import time as time_module
import signal
import pandas as pd
import threading

# Import all components
from config_live import *
from indicator_calculator import IndicatorCalculator
from position_tracker import PositionTracker
from trade_logger import TradeLogger
from paper_order_manager import PaperOrderManager
from live_signal_scanner import LiveSignalScanner
from live_data_streamer import LiveDataStreamer
from strategy_v30 import StrategyV30

if MODE == "LIVE":
    import upstox_client
    from dateutil.parser import parse
    from atm_selector import ATMSelector

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
        self.upstox_api = None
        
        self.strategy = StrategyV30()
        self.indicator_calculator = IndicatorCalculator(
            buffer_size=CANDLE_BUFFER_SIZE, 
            strategy_params=self.strategy.get_config()
        )
        self.position_tracker = PositionTracker()
        self.trade_logger = TradeLogger(TRADE_LOG_DIR)
        self.paper_order_manager = PaperOrderManager(
            self.strategy, 
            self.position_tracker, 
            self.trade_logger
        )
        self.signal_scanner = LiveSignalScanner(
            self.indicator_calculator,
            self.position_tracker  # Pass position tracker for flatness check
        )
        self.data_streamer = LiveDataStreamer(
            access_token=self.access_token,
            instrument_keys={'nifty': NIFTY_INDEX_KEY, 'ce': '', 'pe': ''},
            indicator_calculator=self.indicator_calculator,
            on_candle_closed_callback=self.on_candle_closed
        )
        
        self.atm_config = {}
        self.last_signal = "WAITING..."
        
        title = "PHASE 4: TRUE DATA REPLAY (V30)" if MODE == "MOCK" else "PHASE 3: LIVE PAPER TRADING"
        logger.info("="*70)
        logger.info(f"🔥 TRADER-BADDU - {title}")
        logger.info("="*70)
    
    def initialize_components_live(self):
        """Initializes components needed only for LIVE mode."""
        logger.info("\n" + "="*70 + "\n⚙️  INITIALIZING LIVE COMPONENTS\n" + "="*70)
        # Load access token
        try:
            with open(SESSION_FILE, 'r') as f:
                self.access_token = json.load(f).get('access_token')
            if not self.access_token:
                raise ValueError("No access token found.")
            configuration = upstox_client.Configuration()
            configuration.access_token = self.access_token
            self.upstox_api = upstox_client.ApiClient(configuration)
            logger.info("✅ Access token loaded and API client configured.")
        except Exception as e:
            logger.error(f"❌ Failed to load access token or configure API: {e}")
            return False

        # ATM Selector
        self.atm_selector = ATMSelector(self.access_token)
        if not self.atm_selector.initialize_atm():
            logger.error("❌ ATM initialization failed!")
            return False
        self.atm_config = self.atm_selector.get_current_config()
        self.data_streamer.instrument_keys.update({
            'ce': self.atm_config['ce_key'],
            'pe': self.atm_config['pe_key']
        })
        logger.info("✅ ATM Selector ready.")
        return True

    def on_candle_closed(self, candle_type):
        """
        Callback triggered when a 5-minute candle closes.
        CRITICAL: Execute pending entries BEFORE scanning for new signals
        """
        if candle_type != 'NIFTY':
            return
        
        # In MOCK mode, the ATM strike is dynamic, taken from the data feed
        if MODE == "MOCK":
            prices = self.data_streamer.get_current_prices()
            self.atm_config['strike'] = prices.get('CE', {}).get('strike_price', 'N/A')

        # === STEP 1: Calculate indicators for all instruments ===
        self.indicator_calculator.calculate_nifty_indicators()
        self.indicator_calculator.calculate_option_indicators('CE')
        self.indicator_calculator.calculate_option_indicators('PE')

        # === STEP 2: Update positions FIRST (execute pending T+1 entries) ===
        # This ensures position count is correct when scanner checks
        # Capture if any orders were closed this candle
        closed_orders = self.update_positions()
        
        # === STEP 3: THEN scan for signals (now position count is accurate) ===
        # STRICT CHECK: Only scan if:
        # 1. FLAT (No Open Positions)
        # 2. IDLE (No Pending Signals)
        # 3. STABLE (No trade closed THIS candle - enforces 1-candle cooldown matching Phase 2)
        if (self.position_tracker.get_open_position_count() == 0 and 
            self.paper_order_manager.pending_signal is None and
            not closed_orders):
            
            signal = self.signal_scanner.on_candle_closed(candle_type)
        else:
            signal = None
            
        self.last_signal = signal if signal else "WAITING..."
        
        # === STEP 4: Handle signal (queue for T+1 execution) ===
        if signal:
            self.handle_signal(signal)
        
        # Display dashboard
        self.display_dashboard()

    def handle_signal(self, signal):
        """
        Handle an entry signal by queuing it for T+1 execution.
        FIXED: Passes signal_time to paper_order_manager + logs signal
        """
        logger.info(f"🚥 HANDLING SIGNAL: {signal}")
        
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        signal_time = nifty_indicators.get('timestamp')
        
        # Log the signal for tracking
        prices = self.data_streamer.get_current_prices()
        option_side = signal.split('_')[1]  # 'CE' or 'PE'
        option_ltp = prices.get(option_side, {}).get('ltp', 0)
        
        self.trade_logger.log_signal(
            timestamp=signal_time,
            side=signal,
            nifty_close=nifty_indicators.get('close', 0),
            ema21=nifty_indicators.get(f'ema{self.strategy.EMA_PERIOD}', 0),
            macd_hist=nifty_indicators.get('macd_hist', 0),
            choppiness=0,  # Not used in V30
            option_ltp=option_ltp,
            strike=self.atm_config.get('strike', 'N/A')
        )
        
        # Queue signal for T+1 execution (next candle)
        self.paper_order_manager.on_signal_detected(signal, signal_time)

    def update_positions(self):
        """
        Update P&L for open positions and execute pending T+1 orders.
        CRITICAL FIX: Now passes FULL candle data (open, high, low, close, atr, strike_price)
        """
        prices = self.data_streamer.get_current_prices()
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        current_time = nifty_indicators.get('timestamp')
        
        # === BUILD FULL CANDLE DATA (Required for T+1 execution) ===
        ce_data = {
            'open': prices.get('CE', {}).get('open', 0),
            'close': prices.get('CE', {}).get('close', 0),
            'high': prices.get('CE', {}).get('high', 0),
            'low': prices.get('CE', {}).get('low', 0),
            'atr': self.indicator_calculator.get_option_indicators('CE').get('atr', 0),
            'strike_price': prices.get('CE', {}).get('strike_price', 'N/A')
        }
        
        pe_data = {
            'open': prices.get('PE', {}).get('open', 0),
            'close': prices.get('PE', {}).get('close', 0),
            'high': prices.get('PE', {}).get('high', 0),
            'low': prices.get('PE', {}).get('low', 0),
            'atr': self.indicator_calculator.get_option_indicators('PE').get('atr', 0),
            'strike_price': prices.get('PE', {}).get('strike_price', 'N/A')
        }
        
        # === CRITICAL: Pass FULL candle data to update_positions ===
        # MUST RETURN the closed orders list for the scanner check!
        return self.paper_order_manager.update_positions(
            ce_price=ce_data['close'],
            pe_price=pe_data['close'],
            ce_high=ce_data['high'],
            pe_high=pe_data['high'],
            ce_data=ce_data,  # ✅ FULL candle data for T+1 execution
            pe_data=pe_data,  # ✅ FULL candle data for T+1 execution
            nifty_indicators=nifty_indicators,
            current_candle_time=current_time
        )

    def display_dashboard(self):
        """Display live trading dashboard"""
        prices = self.data_streamer.get_current_prices()
        spot_price = prices.get('NIFTY', {}).get('ltp', 0.0)
        atm_strike = self.atm_config.get('strike', 'N/A')
        
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        sim_time = nifty_indicators.get('timestamp')

        nifty_history = self.indicator_calculator.get_nifty_data().tail(3)
        ce_history = self.indicator_calculator.get_option_data('CE').tail(3)
        pe_history = self.indicator_calculator.get_option_data('PE').tail(3)

        print("="*78 + f"\n=================== 🧪 PHASE 4: TRUE DATA REPLAY (V30) 🧪 ===================\n" + "="*78)
        
        if pd.notna(sim_time):
            print(f"⏰ TIME: {sim_time.strftime('%Y-%m-%d %H:%M')} | 💰 SPOT: {spot_price:.2f} | 🎯 ATM: {atm_strike}")
        else:
            print(f"⏰ TIME: Initializing... | 💰 SPOT: {spot_price:.2f} | 🎯 ATM: {atm_strike}")

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
                ce_ltp = ce_history.iloc[i]['close'] if i < len(ce_history) and not ce_history.empty else '----'
                pe_ltp = pe_history.iloc[i]['close'] if i < len(pe_history) and not pe_history.empty else '----'
                
                ce_str = f"{ce_ltp:.2f}" if isinstance(ce_ltp, (int, float)) else ce_ltp
                pe_str = f"{pe_ltp:.2f}" if isinstance(pe_ltp, (int, float)) else pe_ltp
                
                label = labels[i]
                if i == len(nifty_history) - 1:
                    label += " (SIGNAL CANDLE)"

                print(f"{label} O:{nifty_candle['open']:.2f} C:{nifty_candle['close']:.2f} | [CE] LTP: {ce_str.rjust(7)} | [PE] LTP: {pe_str.rjust(7)}")

        print("-----------------------------------------------------------------------------")
        
        if not nifty_indicators:
            print("📊 INDICATORS: Not yet calculated.")
        else:
            ema_period = self.strategy.get_config().get('ema_period', 21)
            vi_period = self.strategy.get_config().get('vi_period', 21)
            ema_key = f'ema{ema_period}'
            vi_plus_key = f'vi_plus_{vi_period}'
            vi_minus_key = f'vi_minus_{vi_period}'

            print(f"📊 INDICATORS: EMA({ema_period}): {nifty_indicators.get(ema_key, 0.0):.2f} | Vortex: {nifty_indicators.get(vi_plus_key, 0.0):.4f} / {nifty_indicators.get(vi_minus_key, 0.0):.4f}")
        
        print(f"🚥 SIGNAL CHECK: {self.last_signal}")
        
        # Display pending T+1 signal if exists
        if self.paper_order_manager.pending_signal:
            print(f"⏳ PENDING T+1 ORDER: {self.paper_order_manager.pending_signal}")
        
        print("=============================================================================")

    def start_trading_session(self):
        """Starts the main trading loop."""
        logger.info(f"\n{'='*70}\n🚀 STARTING TRADING SESSION ({MODE} MODE)\n{'='*70}")
        
        if not self.data_streamer.start():
            logger.error("❌ Data streamer failed to start. Aborting.")
            return
            
        self.running = True
        logger.info("✅ Entering main execution loop. Waiting for market data...")
        
        prices = {}
        try:
            # In MOCK mode, the streamer controls the loop timing.
            # In LIVE mode, this loop keeps the main thread alive.
            while self.running and self.data_streamer.running:
                prices = self.data_streamer.get_current_prices()
                if MODE == 'LIVE':
                    spot = prices.get('NIFTY', {}).get('ltp', 0.0)
                    pulse_msg = f"⏳ Waiting for 5-min candle close... | Signal: {self.last_signal} | NIFTY LTP: {spot:.2f}"
                    print(pulse_msg, end='\r')
                
                time_module.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\n⌨️ KeyboardInterrupt detected. Initiating shutdown...")
        finally:
            self.shutdown(prices)
        
        logger.info("Exited main trading loop.")

    def shutdown(self, prices):
        """Gracefully shut down the trading session."""
        if not self.running:
            return
        logger.info("\n" + "="*70 + "\n🔌 SHUTTING DOWN TRADING SESSION\n" + "="*70)
        self.running = False
        if self.data_streamer:
            self.data_streamer.disconnect()
        
        self.paper_order_manager.force_close_all_positions(
            ce_price=prices.get('CE', {}).get('ltp', 0),
            pe_price=prices.get('PE', {}).get('ltp', 0)
        )
        
        logger.info("\n💾 Saving final logs...")
        self.trade_logger.save_all(self.position_tracker)
        
        logger.info("\n" + "="*70 + "\n✅ SHUTDOWN COMPLETE!\n" + "="*70)
    
    def run(self):
        """Main entry point to run the trader."""
        if MODE == "LIVE":
            if not self.initialize_components_live():
                return
        self.start_trading_session()


def main():
    """Main function to run the application."""
    trader = LiveTraderMain()
    
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutdown signal received! Initiating graceful shutdown...")
        if trader:
            trader.running = False
            if trader.data_streamer:
                trader.data_streamer.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    trader.run()
    
    print("\n" + "="*70)
    print("✅ TRADER-BADDU SESSION ENDED")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()