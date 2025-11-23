"""
Live Signal Scanner
Detects entry signals in real-time using Strategy V30
"""

import logging
from datetime import datetime
import pandas as pd
import sys
import os

# Add parent directory to path to import strategy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase-2'))
from strategy_v30 import StrategyV30

logger = logging.getLogger(__name__)

class LiveSignalScanner:
    def __init__(self, indicator_calculator):
        """
        Initialize Live Signal Scanner
        
        Args:
            indicator_calculator: IndicatorCalculator instance
        """
        self.indicator_calculator = indicator_calculator
        self.strategy = StrategyV30()
        self.config = self.strategy.get_config()
        
        logger.info("✅ Live Signal Scanner initialized with Strategy V30")
    
    def on_candle_closed(self, candle_type):
        """
        Called when a 5-minute candle closes.
        Calculates indicators and checks for an entry signal using StrategyV30.
        
        Args:
            candle_type: 'NIFTY', 'CE', or 'PE'
        
        Returns:
            str: Signal ('BUY_CE', 'BUY_PE') or None
        """
        # Only check for signals on NIFTY candle close
        if candle_type != 'NIFTY':
            return None
        
        # Calculate indicators for the latest NIFTY candle data
        success = self.indicator_calculator.calculate_nifty_indicators()
        
        if not success:
            logger.warning("⚠️  Cannot calculate indicators yet (not enough candles)")
            return None
        
        # Get the full DataFrame with the new indicators
        nifty_df = self.indicator_calculator.get_nifty_data()
        
        if nifty_df is None or len(nifty_df) < 3:
            logger.debug("⏳ Waiting for sufficient data to check signal...")
            return None
            
        # Check for entry signal using the strategy's logic
        signal = self.strategy.check_entry_signal(nifty_df, len(nifty_df) - 1)
        
        if signal:
            indicators = self.indicator_calculator.get_nifty_indicators() # For logging
            logger.info(f"🚨 SIGNAL DETECTED: {signal}")
            logger.info(f"   NIFTY: {indicators['close']:.2f} | EMA21: {indicators['ema21']:.2f}")
            logger.info(f"   Vortex: {indicators['vi_plus']:.2f} / {indicators['vi_minus']:.2f}")

        return signal
    
    def get_signal_context(self):
        """
        Get current market context for signal generation.
        
        Returns:
            dict: Current indicator values and signal readiness.
        """
        indicators = self.indicator_calculator.get_nifty_indicators()
        
        if not indicators:
            return {'ready': False, 'reason': 'Indicators not calculated'}
        
        return {
            'ready': True,
            'nifty_close': indicators.get('close', 0),
            'ema21': indicators.get('ema21', 0),
            'vi_plus': indicators.get('vi_plus', 0),
            'vi_minus': indicators.get('vi_minus', 0),
            'timestamp': indicators.get('timestamp')
        }