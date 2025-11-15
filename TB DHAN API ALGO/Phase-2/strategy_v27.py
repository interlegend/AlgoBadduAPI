"""
STRATEGY V27 - BUY ONLY EDITION (ENHANCED WITH DYNAMIC TRAILING)
Real Strategy V25 Logic with Professional Risk Management!

Author: Commander Trader-Baddu
Powered by: King Claude AI
Status: PRODUCTION READY WITH DYNAMIC TRAILING ✅
"""

from datetime import time

class StrategyV27:
    """
    Enhanced Strategy V27 - BUY ONLY Mode with Dynamic ATR Trailing
    
    Entry Logic:
    - BUY_CE: 3 consecutive rising MACD histograms + close > EMA21 + Choppiness < 57
    - BUY_PE: 3 consecutive falling MACD histograms + close < EMA21 + Choppiness < 57
    
    Exit Logic:
    - Initial SL: Entry - min(1.5 × ATR, Max SL Cap)
    - TP1: Entry + target points (CE: 15, PE: 10)
    - After TP1: Move SL to breakeven, then trail by 0.4 × ATR
    - MACD/EMA Exit: Only after TP1 hit
    - EOD Exit: 3:25 PM forced close
    """
    
    def __init__(self):
        # Configuration
        self.LOT_SIZE = 75
        self.SL_MULTIPLIER = 1.5
        self.ATR_PERIOD = 14  # 🔥 CHANGED FROM 7 TO 14 FOR STABILITY!
        
        # Target Points (TP1)
        self.TP1_POINTS_CE = 15
        self.TP1_POINTS_PE = 10
        
        # 🔥 NEW: Dynamic Trailing Configuration
        self.TRAIL_ATR_MULTIPLIER = 0.4  # Trail by 40% of ATR
        self.MAX_SL_POINTS = 26.67  # ₹2000 / 75 lot size = 26.67 points max
        
        # Filters
        self.CHOPPINESS_THRESHOLD = 57
        
        # Time windows
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(15, 15)
        self.EOD_EXIT_TIME = time(15, 25)
    
    def check_entry_signal(self, df, idx):
        """
        Check for entry signals based on NIFTY index indicators
        
        Args:
            df: DataFrame with NIFTY data and indicators
            idx: Current candle index
        
        Returns:
            str: "BUY_CE", "BUY_PE", or None
        """
        if idx < 2:  # Need at least 2 previous bars
            return None
        
        row = df.iloc[idx]
        current_time = row['datetime'].time()
        
        # Check time window
        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
            return None
        
        # Get indicator values
        close = row['index_close']
        ema21 = row['ema21']
        hist = row['macd_hist']
        prev1_hist = df['macd_hist'].iloc[idx - 1]
        prev2_hist = df['macd_hist'].iloc[idx - 2]
        choppiness = row['choppiness']
        
        # Check choppiness filter
        if choppiness >= self.CHOPPINESS_THRESHOLD:
            return None
        
        # BUY_CE Signal: 3 consecutive rising histograms
        if (hist > prev1_hist > prev2_hist) and (close > ema21):
            return "BUY_CE"
        
        # BUY_PE Signal: 3 consecutive falling histograms
        if (hist < prev1_hist < prev2_hist) and (close < ema21):
            return "BUY_PE"
        
        return None
    
    def calculate_entry_levels(self, side, entry_price, option_atr):
        """
        Calculate SL and TP1 levels for entry with MAX SL CAP
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            entry_price: Option entry price
            option_atr: ATR calculated on option prices
        
        Returns:
            dict: {'sl': float, 'tp1': float, 'atr_based_sl': float}
        """
        # Calculate ATR-based SL
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        
        # 🔥 APPLY MAX SL CAP OF ₹2000 (26.67 points)
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
            'atr_based_sl': atr_based_sl  # Store original for reference
        }
    
    def calculate_dynamic_trailing_sl(self, highest_price, entry_price, current_sl, option_atr, tp1_hit):
        """
        🔥 NEW METHOD: Calculate dynamic trailing SL based on ATR
        
        Args:
            highest_price: Highest price reached since entry
            entry_price: Original entry price
            current_sl: Current SL level
            option_atr: Current ATR value
            tp1_hit: Whether TP1 has been hit
        
        Returns:
            float: New trailing SL level
        """
        if not tp1_hit:
            return current_sl  # No trailing until TP1 hit
        
        # Trail step is 0.4 × ATR
        trail_step = self.TRAIL_ATR_MULTIPLIER * option_atr
        
        # Calculate new SL based on highest price minus trail step
        new_sl = round(highest_price - trail_step, 2)
        
        # SL can only move up (never down)
        # Also ensure it's at least at breakeven after TP1
        return max(new_sl, current_sl, entry_price)
    
    def check_tp1_hit(self, side, current_high, tp1_level):
        """
        Check if TP1 has been hit
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            current_high: Current candle's high
            tp1_level: TP1 price level
        
        Returns:
            bool: True if TP1 hit
        """
        # For BUY (both CE and PE), TP1 is hit when price reaches target
        return current_high >= tp1_level
    
    def check_sl_hit(self, side, current_close, sl_level):
        """
        Check if Stop Loss has been hit
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            current_close: Current candle's close
            sl_level: SL price level
        
        Returns:
            bool: True if SL hit
        """
        # For BUY (both CE and PE), SL is hit when price falls below SL
        return current_close <= sl_level
    
    def check_macd_ema_exit(self, side, tp1_hit, nifty_close, ema21, macd_hist):
        """
        Check if MACD/EMA exit condition is met (only after TP1)
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            tp1_hit: Whether TP1 has been hit
            nifty_close: Current NIFTY close price
            ema21: EMA21 value
            macd_hist: MACD histogram value
        
        Returns:
            bool: True if should exit
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
        """
        Check if EOD exit time has been reached
        
        Args:
            current_time: Current time
        
        Returns:
            bool: True if should exit
        """
        return current_time >= self.EOD_EXIT_TIME
    
    def calculate_pnl(self, side, entry_price, exit_price):
        """
        Calculate P&L for the trade
        
        Args:
            side: "BUY_CE" or "BUY_PE"
            entry_price: Entry price
            exit_price: Exit price
        
        Returns:
            dict: {'pnl_points': float, 'pnl_inr': float}
        """
        # For BUY trades (both CE and PE): profit when price goes up
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        
        return {
            'pnl_points': round(pnl_points, 2),
            'pnl_inr': round(pnl_inr, 2)
        }
    
    def get_config(self):
        """Return strategy configuration as dict"""
        return {
            'lot_size': self.LOT_SIZE,
            'sl_multiplier': self.SL_MULTIPLIER,
            'atr_period': self.ATR_PERIOD,  # 🔥 NOW RETURNS 14!
            'tp1_ce': self.TP1_POINTS_CE,
            'tp1_pe': self.TP1_POINTS_PE,
            'trail_atr_multiplier': self.TRAIL_ATR_MULTIPLIER,  # 🔥 NEW!
            'max_sl_points': self.MAX_SL_POINTS,  # 🔥 NEW!
            'choppiness_threshold': self.CHOPPINESS_THRESHOLD,
            'entry_start': self.ENTRY_START,
            'entry_end': self.ENTRY_END,
            'eod_exit': self.EOD_EXIT_TIME
        }