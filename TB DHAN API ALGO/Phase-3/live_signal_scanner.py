"""
Live Signal Scanner
Detects entry signals in real-time using Strategy V27
"""

import logging
from datetime import datetime
import pandas as pd
import sys
import os

# Add parent directory to path to import strategy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase-2'))
from strategy_v27 import StrategyV27

logger = logging.getLogger(__name__)

class LiveSignalScanner:
    def __init__(self, indicator_calculator):
        """
        Initialize Live Signal Scanner
        
        Args:
            indicator_calculator: IndicatorCalculator instance
        """
        self.indicator_calculator = indicator_calculator
        self.strategy = StrategyV27()
        self.config = self.strategy.get_config()
        
        # Track last 3 MACD histograms for signal detection
        self.macd_hist_buffer = []
        
        logger.info("✅ Live Signal Scanner initialized with Strategy V27")
    
    def on_candle_closed(self, candle_type):
        """
        Called when a 5-minute candle closes
        
        Args:
            candle_type: 'NIFTY', 'CE', or 'PE'
        
        Returns:
            str: Signal ('BUY_CE', 'BUY_PE') or None
        """
        
        # Only check for signals on NIFTY candle close
        if candle_type != 'NIFTY':
            return None
        
        # Calculate indicators
        success = self.indicator_calculator.calculate_nifty_indicators()
        
        if not success:
            logger.warning("⚠️  Cannot calculate indicators yet (not enough candles)")
            return None
        
        # Get indicator values
        indicators = self.indicator_calculator.get_nifty_indicators()
        
        # Update MACD histogram buffer
        self.macd_hist_buffer.append(indicators['macd_hist'])
        if len(self.macd_hist_buffer) > 3:
            self.macd_hist_buffer.pop(0)
        
        # Need at least 3 values for signal detection
        if len(self.macd_hist_buffer) < 3:
            logger.debug("⏳ Waiting for 3 MACD histogram values...")
            return None
        
        # Check for entry signal
        signal = self._check_entry_signal(indicators)
        
        if signal:
            logger.info(f"🚨 SIGNAL DETECTED: {signal}")
            logger.info(f"   NIFTY: {indicators['close']:.2f} | EMA21: {indicators['ema21']:.2f}")
            logger.info(f"   MACD Hist: {indicators['macd_hist']:.2f} | Choppiness: {indicators['choppiness']:.1f}")
        
        return signal
    
    def _check_entry_signal(self, indicators):
        """
        Check for BUY_CE or BUY_PE signal
        
        Args:
            indicators: Dict with NIFTY indicator values
        
        Returns:
            str: 'BUY_CE', 'BUY_PE', or None
        """
        
        # Check time window
        current_time = datetime.now().time()
        if not (self.config['entry_start'] <= current_time <= self.config['entry_end']):
            return None
        
        close = indicators['close']
        ema21 = indicators['ema21']
        choppiness = indicators['choppiness']
        
        # Get last 3 MACD histograms
        hist = self.macd_hist_buffer[2]      # Current
        prev1_hist = self.macd_hist_buffer[1]  # Previous 1
        prev2_hist = self.macd_hist_buffer[0]  # Previous 2
        
        # Check choppiness filter
        if choppiness >= self.config['choppiness_threshold']:
            return None
        
        # BUY_CE Signal: 3 consecutive rising histograms + close > EMA21
        hist_rising = hist > prev1_hist > prev2_hist
        if hist_rising and close > ema21:
            return "BUY_CE"
        
        # BUY_PE Signal: 3 consecutive falling histograms + close < EMA21
        hist_falling = hist < prev1_hist < prev2_hist
        if hist_falling and close < ema21:
            return "BUY_PE"
        
        return None
    
    def get_signal_context(self):
        """
        Get current market context for signal generation
        
        Returns:
            dict: Current indicator values and signal readiness
        """
        indicators = self.indicator_calculator.get_nifty_indicators()
        
        if not indicators:
            return {'ready': False, 'reason': 'Indicators not calculated'}
        
        macd_trend = "RISING" if len(self.macd_hist_buffer) >= 2 and self.macd_hist_buffer[-1] > self.macd_hist_buffer[-2] else "FALLING"
        
        return {
            'ready': True,
            'nifty_close': indicators.get('close', 0),
            'ema21': indicators.get('ema21', 0),
            'macd_hist': indicators.get('macd_hist', 0),
            'macd_trend': macd_trend,
            'choppiness': indicators.get('choppiness', 0),
            'macd_buffer_size': len(self.macd_hist_buffer),
            'timestamp': indicators.get('timestamp')
        }