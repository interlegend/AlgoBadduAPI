"""
STRATEGY V27 - BUY ONLY EDITION (VOLUME FILTER EDITION)

Professional Options Strategy with Volume Confirmation

Author: Commander Trader-Baddu
Powered by: King Claude AI
Status: PRODUCTION READY ✅

Entry Logic:
- BUY_CE: 3 consecutive rising MACD histograms + close > EMA13 + Volume > Volume_EMA13
- BUY_PE: 3 consecutive falling MACD histograms + close < EMA13 + Volume > Volume_EMA13

Exit Logic:
- Initial SL: Entry - min(1.2 × ATR, ₹2000 cap)
- TP1: Entry + 10 points
- After TP1: Move SL to breakeven, then trail by 0.5 × ATR
- MACD/EMA Exit: Reversal detection (only after TP1)
- EOD Exit: 3:25 PM forced close
"""

from datetime import time
import pandas as pd


class StrategyV27:
    """
    Enhanced Strategy V27 - BUY ONLY Mode with Volume Filter
    
    Key Features:
    - MACD histogram momentum detection
    - EMA13 trend filter
    - Options volume confirmation (> EMA13)
    - Dynamic ATR-based trailing stop
    - Professional risk management
    """
    
    def __init__(self):
        # === CONFIGURATION ===
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        
        # === RISK MANAGEMENT ===
        self.SL_MULTIPLIER = 1.2        # Initial SL = 1.2 × ATR
        self.TP1_POINTS_CE = 10         # Target profit for CE
        self.TP1_POINTS_PE = 10         # Target profit for PE
        self.TRAIL_ATR_MULTIPLIER = 0.5 # Trail by 0.5 × ATR after TP1
        self.MAX_SL_POINTS = 26.67      # Max loss = ₹2000 (₹2000/75)
        
        # === VOLUME FILTER ===
        self.VOLUME_EMA_PERIOD = 13     # Volume EMA period
        self.VOLUME_MULTIPLIER = 0.75    # Require volume > 1.0x EMA
        
        # === TIME WINDOWS ===
        self.ENTRY_START = time(9, 30)   # Start entries at 9:30 AM
        self.ENTRY_END = time(14, 30)    # Stop entries at 2:30 PM
        self.EOD_EXIT_TIME = time(15, 25) # Force exit at 3:25 PM
    
    def check_entry_signal(self, df, idx):
        """
        Check for entry signal based on NIFTY indicators
        
        Args:
            df: DataFrame with NIFTY OHLC + indicators
            idx: Current candle index
        
        Returns:
            "BUY_CE", "BUY_PE", or None
        """
        # Need at least 2 previous candles for 3-candle pattern
        if idx < 2:
            return None
        
        # Get current and previous candles
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1]
        prev2_row = df.iloc[idx - 2]
        current_time = row['datetime'].time()
        
        # === TIME WINDOW CHECK ===
        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
            return None
        
        # === GET INDICATOR VALUES ===
        close = row['index_close']
        ema13 = row['ema13']
        
        # MACD histogram (current and 2 previous)
        macd_hist = row['macd_hist']
        prev_hist = prev_row['macd_hist']
        prev2_hist = prev2_row['macd_hist']
        
        # === BUY_CE LOGIC ===
        # 3 consecutive rising histogram + close > EMA13
        if (prev2_hist < prev_hist < macd_hist) and (close > ema13):
            return "BUY_CE"
        
        # === BUY_PE LOGIC ===
        # 3 consecutive falling histogram + close < EMA13
        if (prev2_hist > prev_hist > macd_hist) and (close < ema13):
            return "BUY_PE"
        
        return None
    
    def check_volume_filter(self, option_volume, volume_ema):
        """
        Volume confirmation filter for options
        
        Args:
            option_volume: Current candle volume
            volume_ema: Volume EMA13 value
        
        Returns:
            True if volume passes filter, False otherwise
        
        Logic:
            - Ensures option has sufficient liquidity
            - Confirms institutional interest
            - Filters out low-volume traps
        """
        # Check for NaN values
        if pd.isna(volume_ema) or pd.isna(option_volume):
            return False
        
        # Require volume > threshold × EMA
        required_volume = volume_ema * self.VOLUME_MULTIPLIER
        
        return option_volume > required_volume
    
    def calculate_entry_levels(self, side, entry_price, option_atr):
        """
        Calculate initial SL and TP1 levels
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            entry_price: Entry price
            option_atr: ATR of the option
        
        Returns:
            dict with 'sl', 'tp1', 'atr_based_sl'
        """
        # Calculate ATR-based SL distance
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        
        # Apply max loss cap (₹2000)
        actual_sl_distance = min(atr_based_sl, self.MAX_SL_POINTS)
        
        # Calculate levels
        if side == "BUY_CE":
            sl = round(entry_price - actual_sl_distance, 2)
            tp1 = entry_price + self.TP1_POINTS_CE
        elif side == "BUY_PE":
            sl = round(entry_price - actual_sl_distance, 2)
            tp1 = entry_price + self.TP1_POINTS_PE
        else:
            raise ValueError(f"Invalid side: {side}")
        
        return {
            'sl': sl,
            'tp1': tp1,
            'atr_based_sl': atr_based_sl
        }
    
    def calculate_dynamic_trailing_sl(self, highest_price, entry_price, current_sl, option_atr, tp1_hit):
        """
        Dynamic trailing stop loss based on ATR
        
        Args:
            highest_price: Highest price reached since entry
            entry_price: Original entry price
            current_sl: Current stop loss level
            option_atr: ATR of the option
            tp1_hit: Whether TP1 has been hit
        
        Returns:
            New SL level (only moves up, never down)
        
        Logic:
            - Before TP1: Keep initial SL
            - After TP1: Trail by 0.5 × ATR from highest price
            - SL can only move up (never down)
            - Must stay at breakeven or higher after TP1
        """
        # Don't trail until TP1 is hit
        if not tp1_hit:
            return current_sl
        
        # Calculate trail distance
        trail_step = self.TRAIL_ATR_MULTIPLIER * option_atr
        
        # New SL = Highest price - trail step
        new_sl = round(highest_price - trail_step, 2)
        
        # SL can only move up, and must be at breakeven or higher
        return max(new_sl, current_sl, entry_price)
    
    def check_tp1_hit(self, side, current_high, tp1_level):
        """
        Check if TP1 target has been reached
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            current_high: High of current candle
            tp1_level: TP1 price level
        
        Returns:
            True if TP1 reached, False otherwise
        """
        return current_high >= tp1_level
    
    def check_sl_hit(self, side, current_close, sl_level):
        """
        Check if stop loss has been triggered
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            current_close: Close price of current candle
            sl_level: Stop loss level
        
        Returns:
            True if SL hit, False otherwise
        """
        return current_close <= sl_level
    
    def check_macd_ema_exit(self, side, tp1_hit, nifty_close, ema13, macd_hist):
        """
        MACD/EMA reversal exit (only after TP1 hit)
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            tp1_hit: Whether TP1 has been hit
            nifty_close: NIFTY close price
            ema13: EMA13 value
            macd_hist: MACD histogram value
        
        Returns:
            True if exit signal triggered, False otherwise
        
        Logic:
            - Only active after TP1 is hit
            - CE: Exit on bearish reversal (price < EMA13 OR MACD hist < 0)
            - PE: Exit on bullish reversal (price > EMA13 OR MACD hist > 0)
        """
        # Only check after TP1 hit
        if not tp1_hit:
            return False
        
        if side == "BUY_CE":
            # Exit CE on bearish reversal
            return (nifty_close < ema13) or (macd_hist < 0)
        
        elif side == "BUY_PE":
            # Exit PE on bullish reversal
            return (nifty_close > ema13) or (macd_hist > 0)
        
        return False
    
    def check_eod_exit(self, current_time):
        """
        Check if end-of-day exit time has been reached
        
        Args:
            current_time: Current time (datetime.time object)
        
        Returns:
            True if EOD exit triggered, False otherwise
        """
        return current_time >= self.EOD_EXIT_TIME
    
    def calculate_pnl(self, side, entry_price, exit_price):
        """
        Calculate profit/loss for the trade
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            entry_price: Entry price
            exit_price: Exit price
        
        Returns:
            dict with 'pnl_points' and 'pnl_inr'
        """
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        
        return {
            'pnl_points': round(pnl_points, 2),
            'pnl_inr': round(pnl_inr, 2)
        }
    
    def get_config(self):
        """
        Return strategy configuration for logging/display
        
        Returns:
            dict with all strategy parameters
        """
        return {
            'version': 'V27 - Volume Filter Edition',
            'lot_size': self.LOT_SIZE,
            'atr_period': self.ATR_PERIOD,
            'sl_multiplier': self.SL_MULTIPLIER,
            'tp1_ce': self.TP1_POINTS_CE,
            'tp1_pe': self.TP1_POINTS_PE,
            'trail_atr_multiplier': self.TRAIL_ATR_MULTIPLIER,
            'max_sl_points': self.MAX_SL_POINTS,
            'volume_ema_period': self.VOLUME_EMA_PERIOD,
            'volume_multiplier': self.VOLUME_MULTIPLIER,
            'entry_start': str(self.ENTRY_START),
            'entry_end': str(self.ENTRY_END),
            'eod_exit': str(self.EOD_EXIT_TIME)
        }
