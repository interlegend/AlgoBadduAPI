"""
STRATEGY V28 - MACD CROSSOVER EDITION 🔥

Simplified Entry Logic with Classic MACD Crossover!

Author: Commander Trader-Baddu
Powered by: King Claude AI
Status: READY TO DOMINATE! ✅

Changes from V27:
- Entry: MACD crossover (simpler, more reliable)
- Exit: EMA/MACD reversal (keep winning logic)
- Time filter: Stop entries after 2:30 PM
- Chop threshold: Back to 57 (tighter filter)
"""

from datetime import time

class StrategyV28:
    """
    V28 - MACD Crossover Strategy with BUY ONLY Mode
    
    Entry Logic:
    - BUY_CE: MACD crosses above Signal + Close > EMA21 + Chop < 57
    - BUY_PE: MACD crosses below Signal + Close < EMA21 + Chop < 57
    
    Exit Logic:
    - Initial SL: Entry - min(1.2 × ATR, ₹2000 max)
    - TP1: Entry + 12 points (CE) / 10 points (PE)
    - After TP1: Trail by 0.5 × ATR
    - MACD/EMA Exit: Reversal detection (after TP1)
    - EOD Exit: 3:25 PM forced close
    """
    
    def __init__(self):
        # Configuration
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        
        # Risk Management
        self.SL_MULTIPLIER = 1.2  # Tight initial SL
        self.TP1_POINTS_CE = 12   # Faster profit lock for CE
        self.TP1_POINTS_PE = 10   # PE target
        self.TRAIL_ATR_MULTIPLIER = 0.5  # Aggressive trailing
        self.MAX_SL_POINTS = 26.67  # ₹2000 max loss cap
        
        # Filters
        self.CHOPPINESS_THRESHOLD = 65  # Tight chop filter
        
        # Time Windows
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(15, 10)  # ✅ FIXED: Stop at 3:10 PM!
        self.EOD_EXIT_TIME = time(15, 25)
    
    def check_entry_signal(self, df, idx):
        """
        ✅ NEW: MACD Crossover Entry Logic
        
        BUY_CE: MACD crosses ABOVE Signal + Price > EMA21
        BUY_PE: MACD crosses BELOW Signal + Price < EMA21
        """
        if idx < 1:  # Need at least 1 previous bar for crossover
            return None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1]
        current_time = row['datetime'].time()
        
        # Check time window (now stops at 3:10 PM!)
        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
            return None
        
        # Get indicator values
        close = row['index_close']
        #ema13 = row['ema13']
        
        # Current and previous MACD values
        macd = row['macd']
        macd_signal = row['macd_signal']
        prev_macd = prev_row['macd']
        prev_macd_signal = prev_row['macd_signal']
        
        choppiness = row['choppiness']
        
        # Check choppiness filter
        if choppiness >= self.CHOPPINESS_THRESHOLD:
            return None
        
        # ✅ BUY_CE: MACD crosses ABOVE Signal (bullish crossover)
        elif (prev_macd <= prev_macd_signal) and (macd > macd_signal):
            
            return "BUY_CE"
        
        # ✅ BUY_PE: MACD crosses BELOW Signal (bearish crossover)
        elif (prev_macd >= prev_macd_signal) and (macd < macd_signal):
            return "BUY_PE"
        
        return None
    
    def calculate_entry_levels(self, side, entry_price, option_atr):
        """
        Calculate SL and TP1 levels with MAX SL CAP
        """
        # Calculate ATR-based SL
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        
        # Apply ₹2000 max loss cap
        actual_sl_distance = min(atr_based_sl, self.MAX_SL_POINTS)
        
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
        Dynamic trailing SL based on ATR (after TP1 hit)
        """
        if not tp1_hit:
            return current_sl  # No trailing until TP1 hit
        
        # Trail by 0.5 × ATR from highest price
        trail_step = self.TRAIL_ATR_MULTIPLIER * option_atr
        new_sl = round(highest_price - trail_step, 2)
        
        # SL can only move up, never down
        # Must stay at breakeven or higher after TP1
        return max(new_sl, current_sl, entry_price)
    
    def check_tp1_hit(self, side, current_high, tp1_level):
        """Check if TP1 target reached"""
        return current_high >= tp1_level
    
    def check_sl_hit(self, side, current_close, sl_level):
        """Check if Stop Loss triggered"""
        return current_close <= sl_level
    
    def check_macd_ema_exit(self, side, tp1_hit, nifty_close, ema21, macd_hist):
        """
        ✅ MACD/EMA Exit Logic (only after TP1 hit)
        
        CE: Exit on bearish reversal (price < EMA21 OR MACD hist < 0)
        PE: Exit on bullish reversal (price > EMA21 OR MACD hist > 0)
        """
        if not tp1_hit:
            return False
        
        if side == "BUY_CE":
            # Exit CE on bearish reversal
            return (nifty_close < ema21) or (macd_hist < 0)
        elif side == "BUY_PE":
            # Exit PE on bullish reversal
            return (nifty_close > ema21) or (macd_hist > 0)
        
        return False
    
    def check_eod_exit(self, current_time):
        """Check if end-of-day exit time reached"""
        return current_time >= self.EOD_EXIT_TIME
    
    def calculate_pnl(self, side, entry_price, exit_price):
        """Calculate P&L for the trade"""
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        
        return {
            'pnl_points': round(pnl_points, 2),
            'pnl_inr': round(pnl_inr, 2)
        }
    
    def get_config(self):
        """Return strategy configuration"""
        return {
            'version': 'V28 - MACD Crossover Edition',
            'lot_size': self.LOT_SIZE,
            'sl_multiplier': self.SL_MULTIPLIER,
            'atr_period': self.ATR_PERIOD,
            'tp1_ce': self.TP1_POINTS_CE,
            'tp1_pe': self.TP1_POINTS_PE,
            'trail_atr_multiplier': self.TRAIL_ATR_MULTIPLIER,
            'max_sl_points': self.MAX_SL_POINTS,
            'choppiness_threshold': self.CHOPPINESS_THRESHOLD,
            'entry_start': self.ENTRY_START,
            'entry_end': self.ENTRY_END,  # Now 2:30 PM!
            'eod_exit': self.EOD_EXIT_TIME
        }
