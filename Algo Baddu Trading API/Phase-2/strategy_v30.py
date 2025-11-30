"""
STRATEGY V28 - VORTEX FILTER CHAMPION

This strategy is the winner of the "Filter Battle Royale," using the Vortex Indicator
as a primary filter to improve signal quality.

Author: Commander Trader-Baddu
Powered by: King Gemini AI
Status: V28 - LATEST & GREATEST ✅

Entry Logic:
- VI Filter: Confirms a new or strengthening trend (VI+ > VI- and widening gap for buys).
- MACD/EMA: Original momentum and trend confirmation.
- BUY_CE: VI Bullish Crossover AND 3 rising MACD hist AND close > EMA13
- BUY_PE: VI Bearish Crossover AND 3 falling MACD hist AND close < EMA13

Exit Logic:
- Same as V27 (ATR-based dynamic SL, TP1, MACD/EMA reversal exit, EOD)
"""

from datetime import time
import pandas as pd


class StrategyV30:
    """
    The version of the strategy with MACD histogram filter removed from entry.
    """
    
    def __init__(self, ema_period=21, vi_period=21, sl_multiplier=2.0, tp_points=10, trail_atr_multiplier=0.5):
        # === TUNABLE INDICATOR PARAMETERS ===
        self.EMA_PERIOD = ema_period
        self.VI_PERIOD = vi_period

        # === TUNABLE RISK PARAMETERS ===
        self.SL_MULTIPLIER = sl_multiplier
        self.TP1_POINTS = tp_points
        self.TRAIL_ATR_MULTIPLIER = trail_atr_multiplier
        
        self.CHOP_THRESHOLD = 57

        # === CORE CONFIGURATION ===
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        self.MAX_SL_POINTS = 25 # Max loss = ₹2000 (₹2000/75)
        
        # === TIME WINDOWS ===
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(15, 10)
        self.EOD_EXIT_TIME = time(15, 25)
    
    def check_entry_signal(self, df, idx):
        """
        Check for entry signal based on NIFTY indicators, using Vortex Indicator as the primary filter.
        (MACD histogram filter removed)
        """
        if idx < 2:
            return None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1]
        prev2_row = df.iloc[idx - 2]
        current_time = row['datetime'].time()
        
        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
            return None

        # FILTER: If market is choppy, DO NOT TRADE
        choppiness = row.get('choppiness', 100)
        if choppiness > self.CHOP_THRESHOLD:
            return None

        vi_plus_col = f'vi_plus_{self.VI_PERIOD}'
        vi_minus_col = f'vi_minus_{self.VI_PERIOD}'

        vi_plus = row[vi_plus_col]
        vi_minus = row[vi_minus_col]
        prev_vi_plus = prev_row[vi_plus_col]
        prev_vi_minus = prev_row[vi_minus_col]

        is_bullish_vortex = False
        is_bearish_vortex = False

        if vi_plus > vi_minus:
            current_gap = vi_plus - vi_minus
            previous_gap = prev_vi_plus - prev_vi_minus
            if current_gap > previous_gap:
                is_bullish_vortex = True
        elif vi_minus > vi_plus:
            current_gap = vi_minus - vi_plus
            previous_gap = prev_vi_minus - prev_vi_plus
            if current_gap > previous_gap:
                is_bearish_vortex = True

        if is_bullish_vortex or is_bearish_vortex:
            close = row['index_close']
            ema_col = f'ema{self.EMA_PERIOD}'
            ema = row[ema_col]
            
            # MACD histogram (current and 2 previous)
            macd_hist = row['macd_hist']
            prev_hist = prev_row['macd_hist']
            prev2_hist = prev2_row['macd_hist']
            
            # Removed MACD hist filter
            if is_bullish_vortex and (close > ema): # Removed: (prev2_hist < prev_hist < macd_hist)
                return "BUY_CE"
            
            # Removed MACD hist filter
            if is_bearish_vortex and (close < ema): # Removed: (prev2_hist > prev_hist > macd_hist)
                return "BUY_PE"
        
        return None
    
    def calculate_entry_levels(self, side, entry_price, option_atr):
        """
        Calculate initial SL and TP1 levels
        """
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        actual_sl_distance = min(atr_based_sl, self.MAX_SL_POINTS)
        
        sl = round(entry_price - actual_sl_distance, 2)
        tp1 = entry_price + self.TP1_POINTS
        
        return {'sl': sl, 'tp1': tp1, 'atr_based_sl': atr_based_sl}
    
    def check_tp1_hit(self, side, current_high, tp1_level):
        """Check if TP1 target has been reached"""
        return current_high >= tp1_level
    
    def check_sl_hit(self, side, current_close, sl_level):
        """Check if stop loss has been triggered"""
        return current_close <= sl_level
    
    def check_macd_ema_exit(self, side, tp1_hit, nifty_close, ema, macd_hist):
        """MACD/EMA reversal exit (only after TP1 hit)"""
        if not tp1_hit:
            return False
        
        if side == "BUY_CE":
            return (nifty_close < ema) or (macd_hist < 0)
        elif side == "BUY_PE":
            return (nifty_close > ema) or (macd_hist > 0)
        return False
    
    def check_eod_exit(self, current_time):
        """Check if end-of-day exit time has been reached"""
        return current_time >= self.EOD_EXIT_TIME
    
    def calculate_pnl(self, side, entry_price, exit_price):
        """Calculate profit/loss for the trade with Slippage & Brokerage"""
        pnl_points = exit_price - entry_price
        
        # --- FINANCIAL REALISM ---
        # Slippage: 0.5 pts (approx ₹37.50 for 75 qty)
        # Brokerage & Taxes: ₹50.00
        TOTAL_COST = 87.50 
        
        gross_pnl = pnl_points * self.LOT_SIZE
        net_pnl = gross_pnl - TOTAL_COST
        
        return {
            'pnl_points': round(pnl_points, 2), 
            'pnl_inr': round(net_pnl, 2),
            'gross_pnl': round(gross_pnl, 2),
            'cost': TOTAL_COST
        }
    
    def get_config(self):
        """Return strategy configuration for logging/display"""
        return {
            'version': 'V30 - MACD Filter Removed',
            'ema_period': self.EMA_PERIOD,
            'vi_period': self.VI_PERIOD,
            'sl_multiplier': self.SL_MULTIPLIER,
            'tp1_points': self.TP1_POINTS,
            'trail_atr_multiplier': self.TRAIL_ATR_MULTIPLIER,
            'lot_size': self.LOT_SIZE,
            'atr_period': self.ATR_PERIOD,
            'max_sl_points': self.MAX_SL_POINTS,
            'entry_start': str(self.ENTRY_START),
            'entry_end': str(self.ENTRY_END),
            'eod_exit': str(self.EOD_EXIT_TIME)
        }
