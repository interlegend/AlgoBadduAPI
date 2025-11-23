"""
STRATEGY V30 - Final Backtest Version
"""
from datetime import time, date
import pandas as pd

class StrategyV30:
    def __init__(self, ema_period=21, vi_period=21, sl_multiplier=2.0, tp_points=10, trail_atr_multiplier=0.5):
        self.EMA_PERIOD = ema_period
        self.VI_PERIOD = vi_period
        self.SL_MULTIPLIER = sl_multiplier
        self.TP1_POINTS = tp_points
        self.TRAIL_ATR_MULTIPLIER = trail_atr_multiplier
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        self.MAX_SL_POINTS = 26.67
        # === TIME WINDOWS ===
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(15, 10)
        self.EOD_EXIT_TIME = time(15, 25)

    def check_entry_signal(self, df, idx):
        if idx < 2:
            return None
        
        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1]

        if pd.isna(row['timestamp']):
            return None
        
        current_time = row['timestamp'].time()
        
        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
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
        
        ema_val = row[f'ema{self.EMA_PERIOD}']
        if is_bullish_vortex or is_bearish_vortex:
            # Handle column name differences between Phase 2 (index_close) and Phase 4 (close)
            close_col = 'index_close' if 'index_close' in row else 'close'
            close = row[close_col]
            
            ema_col = f'ema{self.EMA_PERIOD}'
            ema = row[ema_col]
            
            # MACD histogram (current and 2 previous)
            macd_hist = row['macd_hist']

        if is_bullish_vortex and (close > ema_val):
            return "BUY_CE"
        
        if is_bearish_vortex and (close < ema_val):
            return "BUY_PE"
        
        return None

    def calculate_entry_levels(self, side, entry_price, option_atr):
        atr_based_sl = self.SL_MULTIPLIER * option_atr
        actual_sl_distance = min(atr_based_sl, self.MAX_SL_POINTS)
        sl = round(entry_price - actual_sl_distance, 2)
        tp1 = entry_price + self.TP1_POINTS
        return {'sl': sl, 'tp1': tp1, 'atr_based_sl': atr_based_sl}

    def check_tp1_hit(self, side, current_high, tp1_level):
        return current_high >= tp1_level

    def check_sl_hit(self, side, current_close, sl_level):
        return current_close <= sl_level

    def check_macd_ema_exit(self, side, tp1_hit, nifty_close, ema, macd_hist):
        if not tp1_hit:
            return False
        if side == "BUY_CE":
            return (nifty_close < ema) or (macd_hist < 0)
        elif side == "BUY_PE":
            return (nifty_close > ema) or (macd_hist > 0)
        return False

    def check_eod_exit(self, current_time):
        return current_time >= self.EOD_EXIT_TIME

    def calculate_pnl(self, side, entry_price, exit_price):
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        return {'pnl_points': round(pnl_points, 2), 'pnl_inr': round(pnl_inr, 2)}

    def get_config(self):
        return {
            'version': 'V30 - Widening Gap',
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