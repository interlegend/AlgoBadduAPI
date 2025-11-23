"""
Live Signal Scanner - FIXED VERSION
Detects entry signals in real-time using Strategy V30
TASK C: Verified ENTRY_START = 09:30, ENTRY_END = 15:10
"""

import logging
from datetime import datetime
import pandas as pd
import sys
import os

# Import strategy from local directory (Phase-4)
from strategy_v30 import StrategyV30

logger = logging.getLogger(__name__)

class LiveSignalScanner:
    def __init__(self, indicator_calculator, position_tracker=None):
        """
        Initialize Live Signal Scanner
        
        Args:
            indicator_calculator: IndicatorCalculator instance
            position_tracker: PositionTracker instance (to check if flat)
        """
        self.indicator_calculator = indicator_calculator
        self.position_tracker = position_tracker
        self.strategy = StrategyV30()
        self.config = self.strategy.get_config()
        
        # Verify critical time windows
        logger.info("✅ Live Signal Scanner initialized with Strategy V30")
        logger.info(f"   Entry Window: {self.config['entry_start']} to {self.config['entry_end']}")
        logger.info(f"   EOD Exit: {self.config['eod_exit']}")
    
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
        
        # === POSITION FLATNESS CHECK ===
        # Only scan for signals if we have no open positions (to avoid signal spam)
        if self.position_tracker:
            if self.position_tracker.get_open_position_count() > 0:
                return None  # Already in a trade, don't scan
        
        # === CRITICAL: Calculate indicators with stability gate ===
        success = self.indicator_calculator.calculate_nifty_indicators()
        
        if not success:
            # Stability gate blocked - not enough candles or NaN values
            return None
        
        # Get the full DataFrame with the new indicators
        nifty_df = self.indicator_calculator.get_nifty_data()
        
        if nifty_df is None or len(nifty_df) < 3:
            logger.debug("⏳ Waiting for sufficient data to check signal...")
            return None
            
        # Check for entry signal using the strategy's logic
        signal = self.strategy.check_entry_signal(nifty_df, len(nifty_df) - 1)
        
        if signal:
            indicators = self.indicator_calculator.get_nifty_indicators()
            
            # Construct dynamic key names based on strategy parameters
            vi_period = self.strategy.get_config().get('vi_period', 21)
            vi_plus_key = f'vi_plus_{vi_period}'
            vi_minus_key = f'vi_minus_{vi_period}'
            ema_key = f'ema{self.strategy.EMA_PERIOD}'

            # DEBUG: Check previous candle's VI to confirm real crossover
            prev_vi_plus = self.indicator_calculator.get_nifty_data().iloc[-2][vi_plus_key]
            prev_vi_minus = self.indicator_calculator.get_nifty_data().iloc[-2][vi_minus_key]
            curr_vi_plus = indicators.get(vi_plus_key, 0)
            curr_vi_minus = indicators.get(vi_minus_key, 0)
            
            prev_gap = prev_vi_plus - prev_vi_minus
            curr_gap = curr_vi_plus - curr_vi_minus
            
            logger.info("🚨 SIGNAL DETECTED: " + signal)
            logger.info(f"   Time: {indicators['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   NIFTY: {indicators['close']:.2f} | EMA({self.strategy.EMA_PERIOD}): {indicators.get(ema_key, 0):.2f}")
            logger.info(f"   VI+ Prev: {prev_vi_plus:.4f} → Curr: {curr_vi_plus:.4f}")
            logger.info(f"   VI- Prev: {prev_vi_minus:.4f} → Curr: {curr_vi_minus:.4f}")
            logger.info(f"   Gap Prev: {prev_gap:.4f} → Curr: {curr_gap:.4f} | Widening: {curr_gap > prev_gap}")
        
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
        
        ema_period = self.strategy.EMA_PERIOD
        vi_period = self.strategy.VI_PERIOD
        
        return {
            'ready': True,
            'nifty_close': indicators.get('close', 0),
            f'ema{ema_period}': indicators.get(f'ema{ema_period}', 0),
            f'vi_plus_{vi_period}': indicators.get(f'vi_plus_{vi_period}', 0),
            f'vi_minus_{vi_period}': indicators.get(f'vi_minus_{vi_period}', 0),
            'timestamp': indicators.get('timestamp')
        }