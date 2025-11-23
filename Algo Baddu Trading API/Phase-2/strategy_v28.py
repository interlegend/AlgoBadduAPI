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


class StrategyV28:
    """
    Enhanced Strategy V28 - Champion of the Filter Battle Royale.
    
    Key Features:
    - Vortex Indicator for high-quality trend identification.
    - MACD histogram momentum detection.
    - EMA13 trend filter.
    - Dynamic ATR-based trailing stop.
    - Professional risk management.
    """
    
    def __init__(self, ema_period=21, vi_period=21):
        # === TUNABLE PARAMETERS ===
        self.EMA_PERIOD = ema_period
        self.VI_PERIOD = vi_period # Vortex Indicator period

        # === CORE CONFIGURATION ===
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        
        # === RISK MANAGEMENT ===
        self.SL_MULTIPLIER = 1.2
        self.TP1_POINTS_CE = 10
        self.TP1_POINTS_PE = 10
        self.TRAIL_ATR_MULTIPLIER = 0.5
        self.MAX_SL_POINTS = 26.67
        
        # === TIME WINDOWS ===
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(14, 30)
        self.EOD_EXIT_TIME = time(15, 25)
    
    def check_entry_signal(self, df, idx):
        """
        Check for entry signal based on NIFTY indicators, using Vortex Indicator as the primary filter.
        
        Args:
            df: DataFrame with NIFTY OHLC + indicators
            idx: Current candle index
        
        Returns:
            "BUY_CE", "BUY_PE", or None
        """
        # Need at least 2 previous candles for VI gap and MACD pattern
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

        # === VORTEX INDICATOR FILTER ===
        vi_plus_col = f'vi_plus_{self.VI_PERIOD}'
        vi_minus_col = f'vi_minus_{self.VI_PERIOD}'

        vi_plus = row[vi_plus_col]
        vi_minus = row[vi_minus_col]
        prev_vi_plus = prev_row[vi_plus_col]
        prev_vi_minus = prev_row[vi_minus_col]

        is_bullish_vortex = False
        is_bearish_vortex = False

        # Check for bullish vortex signal (VI+ > VI- and gap is widening)
        if vi_plus > vi_minus:
            current_gap = vi_plus - vi_minus
            previous_gap = prev_vi_plus - prev_vi_minus
            if current_gap > previous_gap:
                is_bullish_vortex = True

        # Check for bearish vortex signal (VI- > VI+ and gap is widening)
        elif vi_minus > vi_plus:
            current_gap = vi_minus - vi_plus
            previous_gap = prev_vi_minus - prev_vi_plus
            if current_gap > previous_gap:
                is_bearish_vortex = True

        # === GET INDICATOR VALUES (Only if a vortex signal exists) ===
        if is_bullish_vortex or is_bearish_vortex:
            close = row['index_close']
            ema_col = f'ema{self.EMA_PERIOD}'
            ema = row[ema_col]
            
            # MACD histogram (current and 2 previous)
            macd_hist = row['macd_hist']
            prev_hist = prev_row['macd_hist']
            prev2_hist = prev2_row['macd_hist']
            
            # === BUY_CE LOGIC ===
            # Vortex is bullish AND original MACD/EMA conditions are met
            if is_bullish_vortex and (prev2_hist < prev_hist < macd_hist) and (close > ema):
                return "BUY_CE"
            
            # === BUY_PE LOGIC ===
            # Vortex is bearish AND original MACD/EMA conditions are met
            if is_bearish_vortex and (prev2_hist > prev_hist > macd_hist) and (close < ema):
                return "BUY_PE"
        
        return None
    
    def calculate_entry_levels(self, side, entry_price, option_atr):
        """
        Calculate initial SL and TP1 levels
        """
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        actual_sl_distance = min(atr_based_sl, self.MAX_SL_POINTS)
        
        if side == "BUY_CE":
            sl = round(entry_price - actual_sl_distance, 2)
            tp1 = entry_price + self.TP1_POINTS_CE
        elif side == "BUY_PE":
            sl = round(entry_price - actual_sl_distance, 2)
            tp1 = entry_price + self.TP1_POINTS_PE
        else:
            raise ValueError(f"Invalid side: {side}")
        
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
        """Calculate profit/loss for the trade"""
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        return {'pnl_points': round(pnl_points, 2), 'pnl_inr': round(pnl_inr, 2)}
    
    def get_config(self):
        """Return strategy configuration for logging/display"""
        return {
            'version': 'V28 - Vortex Filter Champion',
            'ema_period': self.EMA_PERIOD,
            'vi_period': self.VI_PERIOD,
            'lot_size': self.LOT_SIZE,
            'atr_period': self.ATR_PERIOD,
            'sl_multiplier': self.SL_MULTIPLIER,
            'tp1_ce': self.TP1_POINTS_CE,
            'tp1_pe': self.TP1_POINTS_PE,
            'trail_atr_multiplier': self.TRAIL_ATR_MULTIPLIER,
            'max_sl_points': self.MAX_SL_POINTS,
            'entry_start': str(self.ENTRY_START),
            'entry_end': str(self.ENTRY_END),
            'eod_exit': str(self.EOD_EXIT_TIME)
        }