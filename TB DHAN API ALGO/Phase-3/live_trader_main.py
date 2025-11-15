"""
LIVE TRADER MAIN
Main orchestrator for Phase 3 Live Paper Trading
Coordinates all components and manages trading session

Author: Commander Trader-Baddu
Powered by: King Claude AI
"""

import os
import sys
import json
import logging
from datetime import datetime, time
import time as time_module
import signal
import pandas as pd

# Add parent directories to path
# Add parent directories to path (SIMPLIFIED!)
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
from strategy_v27 import StrategyV27

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f'live_trader_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'  # ✅ Fix encoding
        ),
        logging.StreamHandler() if CONSOLE_OUTPUT else logging.NullHandler()
    ]
)

# ✅ Fix console encoding for Windows
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)


class LiveTraderMain:
    def __init__(self):
        """Initialize Live Trader"""
        
        self.access_token = None
        self.running = False
        
        # Components
        self.atm_selector = None
        self.indicator_calculator = None
        self.position_tracker = None
        self.trade_logger = None
        self.strategy = None
        self.paper_order_manager = None
        self.signal_scanner = None
        self.data_streamer = None
        
        # Market data
        self.atm_config = {}
        
        logger.info("="*70)
        logger.info("🔥 TRADER-BADDU LIVE PAPER TRADER - PHASE 3")
        logger.info("="*70)
    
    def load_access_token(self):
        """Load Upstox access token"""
        try:
            with open(SESSION_FILE, 'r') as f:
                session = json.load(f)
                self.access_token = session.get('access_token')
            
            if not self.access_token:
                raise ValueError("No access token found!")
            
            logger.info("✅ Access token loaded")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load access token: {e}")
            return False
    
    def initialize_components(self):
        """Initialize all trading components"""
        
        logger.info("\n" + "="*70)
        logger.info("⚙️  INITIALIZING COMPONENTS")
        logger.info("="*70)
        
        # 1. ATM Selector
        logger.info("\n[1/8] Initializing ATM Selector...")
        self.atm_selector = ATMSelector(self.access_token)
        
        if not self.atm_selector.initialize_atm():
            logger.error("❌ ATM initialization failed!")
            return False
        
        self.atm_config = self.atm_selector.get_current_config()
        logger.info("✅ ATM Selector ready")
        
        # 2. Indicator Calculator
        logger.info("\n[2/8] Initializing Indicator Calculator...")
        self.indicator_calculator = IndicatorCalculator(buffer_size=CANDLE_BUFFER_SIZE)
        logger.info("✅ Indicator Calculator ready")
        
        # 3. Position Tracker
        logger.info("\n[3/8] Initializing Position Tracker...")
        self.position_tracker = PositionTracker()
        logger.info("✅ Position Tracker ready")
        
        # 4. Trade Logger
        logger.info("\n[4/8] Initializing Trade Logger...")
        self.trade_logger = TradeLogger(TRADE_LOG_DIR)
        logger.info("✅ Trade Logger ready")
        
        # 5. Strategy V27
        logger.info("\n[5/8] Initializing Strategy V27...")
        self.strategy = StrategyV27()
        strategy_config = self.strategy.get_config()
        logger.info(f"   Lot Size: {strategy_config['lot_size']}")
        logger.info(f"   CE TP1: {strategy_config['tp1_ce']} | PE TP1: {strategy_config['tp1_pe']}")
        logger.info("✅ Strategy V27 ready")
        
        # 6. Paper Order Manager
        logger.info("\n[6/8] Initializing Paper Order Manager...")
        self.paper_order_manager = PaperOrderManager(
            self.strategy,
            self.position_tracker,
            self.trade_logger
        )
        logger.info("✅ Paper Order Manager ready")
        
        # 7. Signal Scanner
        logger.info("\n[7/8] Initializing Live Signal Scanner...")
        self.signal_scanner = LiveSignalScanner(self.indicator_calculator)
        logger.info("✅ Signal Scanner ready")
        
        # 8. Data Streamer
        logger.info("\n[8/8] Initializing Live Data Streamer...")
        
        instrument_keys = {
            'nifty': NIFTY_INDEX_KEY,
            'ce': self.atm_config['ce_key'],
            'pe': self.atm_config['pe_key']
        }
        
        self.data_streamer = LiveDataStreamer(
            access_token=self.access_token,
            instrument_keys=instrument_keys,
            indicator_calculator=self.indicator_calculator,
            on_candle_closed_callback=self.on_candle_closed
        )
        logger.info("✅ Data Streamer ready")
        
        logger.info("\n" + "="*70)
        logger.info("✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY!")
        logger.info("="*70)
        
        return True
    
    def warmup_indicators(self):
        """Fetch historical candles to warmup indicators"""
        
        logger.info("\n" + "="*70)
        logger.info("📊 WARMING UP INDICATORS")
        logger.info("="*70)
        
        # TODO: Fetch last 50 candles using Historical Data API
        # For now, we'll skip warmup and build indicators live
        
        logger.info("⚠️  Warmup skipped - indicators will build live")
        logger.info("   (Need ~10-15 candles for full indicator readiness)")
        
        return True
    
    def on_candle_closed(self, candle_type):
        """
        Callback when a 5-minute candle closes
        
        Args:
            candle_type: 'NIFTY', 'CE', or 'PE'
        """
        
        logger.info(f"🔔 {candle_type} Candle Closed @ {datetime.now().strftime('%H:%M:%S')}")
        
        # Check for entry signal
        signal = self.signal_scanner.on_candle_closed(candle_type)
        
        if signal:
            self.handle_signal(signal)
        
        # Update open positions
        self.update_positions()
        
        # Display dashboard
        self.display_dashboard()
    
    def handle_signal(self, signal):
        """
        Handle entry signal
        
        Args:
            signal: 'BUY_CE' or 'BUY_PE'
        """
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🚨 SIGNAL DETECTED: {signal}")
        logger.info(f"{'='*70}")
        
        # Get current prices
        prices = self.data_streamer.get_current_prices()
        
        # Get NIFTY indicators
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        
        # Get option price and ATR
        if signal == 'BUY_CE':
            option_price = prices['CE']['ltp'] if prices['CE'] else None
            option_indicators = self.indicator_calculator.get_option_indicators('CE')
        elif signal == 'BUY_PE':
            option_price = prices['PE']['ltp'] if prices['PE'] else None
            option_indicators = self.indicator_calculator.get_option_indicators('PE')
        else:
            return
        
        if not option_price or not option_indicators:
            logger.warning("⚠️  Cannot execute - missing price/ATR data")
            return
        
        option_atr = option_indicators.get('atr')
        
        if not option_atr or pd.isna(option_atr):
            logger.warning("⚠️  Cannot execute - ATR not available yet")
            return
        
        # Log signal
        self.trade_logger.log_signal(
            timestamp=datetime.now(),
            side=signal,
            nifty_close=nifty_indicators['close'],
            ema21=nifty_indicators['ema21'],
            macd_hist=nifty_indicators['macd_hist'],
            choppiness=nifty_indicators['choppiness'],
            option_ltp=option_price,
            strike=self.atm_config['strike']
        )
        
        # Create paper order
        order_id = self.paper_order_manager.create_paper_order(
            signal=signal,
            option_price=option_price,
            option_atr=option_atr,
            strike=self.atm_config['strike'],
            signal_time=datetime.now()
        )
        
        if order_id:
            logger.info(f"✅ Paper order created: {order_id}")
        else:
            logger.warning("⚠️  Order not created (max positions reached?)")
    
    def update_positions(self):
        """Update all open positions"""
        
        if self.position_tracker.get_open_position_count() == 0:
            return
        
        # Get current prices
        prices = self.data_streamer.get_current_prices()
        
        if not prices['CE'] or not prices['PE']:
            return
        
        ce_price = prices['CE']['ltp']
        pe_price = prices['PE']['ltp']
        ce_high = prices['CE']['high']
        pe_high = prices['PE']['high']
        
        # Get NIFTY indicators
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        
        # Update positions
        closed_orders = self.paper_order_manager.update_positions(
            ce_price=ce_price,
            pe_price=pe_price,
            ce_high=ce_high,
            pe_high=pe_high,
            nifty_indicators=nifty_indicators
        )
        
        if closed_orders:
            logger.info(f"📊 {len(closed_orders)} position(s) closed this candle")
    
    def display_dashboard(self):
        """Display live trading dashboard"""
        
        stats = self.position_tracker.get_daily_stats()
        open_positions = self.position_tracker.get_all_open_positions()
        prices = self.data_streamer.get_current_prices()
        nifty_indicators = self.indicator_calculator.get_nifty_indicators()
        
        print("\n" + "="*70)
        print("🔥 TRADER-BADDU LIVE DASHBOARD")
        print("="*70)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d')} | ⏰ {datetime.now().strftime('%H:%M:%S')}")
        print(f"🎯 Strike: {self.atm_config['strike']} | 📊 Expiry: {self.atm_config['expiry']}")
        print("="*70)
        
        # Market Data
        if nifty_indicators and prices['NIFTY']:
            print(f"\n📡 MARKET DATA:")
            print(f"   NIFTY: {prices['NIFTY']['ltp']:.2f} | EMA21: {nifty_indicators['ema21']:.2f} | MACD: {nifty_indicators['macd_hist']:.2f}")
            print(f"   {self.atm_config['strike']} CE: ₹{prices['CE']['ltp']:.2f}" if prices['CE'] else "   CE: N/A")
            print(f"   {self.atm_config['strike']} PE: ₹{prices['PE']['ltp']:.2f}" if prices['PE'] else "   PE: N/A")
            print(f"   Choppiness: {nifty_indicators['choppiness']:.1f}")
        
        # Open Positions
        print(f"\n💼 OPEN POSITIONS ({len(open_positions)}):")
        if open_positions:
            for pos in open_positions:
                pnl_emoji = "🟢" if pos['unrealized_pnl_inr'] > 0 else "🔴"
                tp1_emoji = "✅" if pos['tp1_hit'] else "⏳"
                print(f"   {pnl_emoji} {pos['order_id']} | {pos['side']} {pos['strike']} | Entry: ₹{pos['entry_price']:.2f} | CMP: ₹{pos['current_price']:.2f}")
                print(f"      SL: ₹{pos['sl']:.2f} | TP1: {tp1_emoji} | P&L: ₹{pos['unrealized_pnl_inr']:+,.2f}")
        else:
            print("   No open positions")
        
        # Daily Stats
        print(f"\n📊 TODAY'S SUMMARY:")
        print(f"   Trades: {stats['total_trades']} | Winners: {stats['winners']} | Losers: {stats['losers']} | WR: {stats['win_rate']:.1f}%")
        print(f"   Realized P&L: ₹{stats['realized_pnl']:+,.2f} | Unrealized: ₹{stats['unrealized_pnl']:+,.2f}")
        print(f"   Total P&L: ₹{stats['total_pnl']:+,.2f}")
        
        print("="*70 + "\n")
    
    def start_trading_session(self):
        """Start live trading session"""
        
        logger.info("\n" + "="*70)
        logger.info("🚀 STARTING LIVE TRADING SESSION")
        logger.info("="*70)
        
        # Connect to WebSocket
        if not self.data_streamer.connect():
            logger.error("❌ Failed to connect to WebSocket!")
            return False
        
        self.running = True
        
        logger.info("\n✅ LIVE TRADING SESSION ACTIVE!")
        logger.info("   Press Ctrl+C to stop\n")
        
        # Main loop
        try:
            while self.running:
                # Check if market is open
                if not self.data_streamer.is_market_open():
                    if datetime.now().time() > EOD_EXIT_TIME:
                        logger.info("🔔 Market closed - ending session")
                        break
                
                # Sleep for a bit
                time_module.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n🛑 Keyboard interrupt received!")
        
        # Graceful shutdown
        self.shutdown()
        
        return True
    
    def shutdown(self):
        """Gracefully shutdown trading session"""
        
        logger.info("\n" + "="*70)
        logger.info("🔌 SHUTTING DOWN TRADING SESSION")
        logger.info("="*70)
        
        self.running = False
        
        # Force close all positions
        if self.position_tracker.get_open_position_count() > 0:
            logger.info("\n⚠️  Closing all open positions...")
            prices = self.data_streamer.get_current_prices()
            
            ce_price = prices['CE']['ltp'] if prices['CE'] else 0
            pe_price = prices['PE']['ltp'] if prices['PE'] else 0
            
            self.paper_order_manager.force_close_all_positions(ce_price, pe_price)
        
        # Disconnect WebSocket
        if self.data_streamer:
            self.data_streamer.disconnect()
        
        # Save all logs
        logger.info("\n💾 Saving logs...")
        self.trade_logger.save_all(self.position_tracker)
        
        logger.info("\n" + "="*70)
        logger.info("✅ SHUTDOWN COMPLETE!")
        logger.info("="*70)
    
    def run(self):
        """Main entry point"""
        
        try:
            # Load access token
            if not self.load_access_token():
                return
            
            # Initialize components
            if not self.initialize_components():
                return
            
            # Warmup indicators
            if not self.warmup_indicators():
                return
            
            # Start trading
            self.start_trading_session()
            
        except Exception as e:
            logger.error(f"\n💥 FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            if self.data_streamer:
                self.data_streamer.disconnect()


def main():
    """Main function"""
    
    # Print banner
    print("\n" + "🔥"*35)
    print("   TRADER-BADDU LIVE PAPER TRADER")
    print("   Phase 3: Real-Time Signal Detection")
    print("   Strategy V27 - BUY ONLY Mode")
    print("🔥"*35 + "\n")
    
    # Create and run trader
    trader = LiveTraderMain()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutdown signal received!")
        trader.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    trader.run()
    
    print("\n" + "="*70)
    print("✅ TRADER-BADDU SESSION ENDED")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()