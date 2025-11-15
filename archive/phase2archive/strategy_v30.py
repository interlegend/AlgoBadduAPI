"""
STRATEGY V30: DUAL STRATEGY SYSTEM
Two strategies running SIMULTANEOUSLY:
- Scout Mode (BB Mean Reversion - ALWAYS ACTIVE)
- Rumbling Mode (MACD Trend Following - ONLY when choppiness < threshold)
"""
from datetime import time


class StrategyV30:
    def __init__(self):
        # --- Core Config ---
        self.LOT_SIZE = 75
        self.ATR_PERIOD = 14
        self.ENTRY_START = time(9, 30)
        self.ENTRY_END = time(15, 15)
        self.EOD_EXIT_TIME = time(15, 25)
        
        # --- Rumbling Mode Filter ---
        self.RUMBLING_CHOPPINESS_THRESHOLD = 50  # Only enter Rumbling when chop < 50

        # --- Scout Mode Config (BB Mean Reversion) ---
        self.SCOUT_SL_MULTIPLIER = 1.0
        self.SCOUT_TP1_POINTS = 22
        self.SCOUT_TRAIL_ATR_MULTIPLIER = 0.5
        self.SCOUT_MIN_TRAIL_POINTS = 10

        # --- Rumbling Mode Config (MACD Trend Following) ---
        self.RUMBLING_SL_MULTIPLIER = 1.5
        self.RUMBLING_BREAKEVEN_TRIGGER_POINTS = 15
        self.RUMBLING_TRAIL_ATR_MULTIPLIER = 1.0
        self.RUMBLING_MIN_TRAIL_POINTS = 15

    def check_entry_signal(self, df, idx):
        """
        Check BOTH strategies and return whichever fires first.
        Priority: Scout (if signal) > Rumbling (if signal)
        """
        if idx < 26:
            return None

        row = df.iloc[idx]
        current_time = row['datetime'].time()

        if not (self.ENTRY_START <= current_time <= self.ENTRY_END):
            return None

        # 🔥 CHECK SCOUT FIRST (NO CHOPPINESS FILTER!)
        scout_signal = self.check_scout_entry(df, idx)
        if scout_signal:
            return scout_signal
        
        # 🔥 THEN CHECK RUMBLING (WITH CHOPPINESS FILTER!)
        rumbling_signal = self.check_rumbling_entry(df, idx)
        if rumbling_signal:
            return rumbling_signal
        
        return None

    def check_scout_entry(self, df, idx):
        """
        Scout Mode: BB Mean Reversion (ALWAYS ACTIVE - NO CHOP FILTER!)
        """
        row = df.iloc[idx]
        close = row['index_close']
        bb_upper = row['bb_upper']
        bb_lower = row['bb_lower']

        # 🔥 NO CHOPPINESS FILTER!
        # BB mean reversion works in ALL market conditions!
        
        # BUY_CE: At or below lower band (oversold)
        if close <= bb_lower * 1.01:
            return {'signal': 'BUY_CE', 'mode': 'scout'}
        
        # BUY_PE: At or above upper band (overbought)
        if close >= bb_upper * 0.99:
            return {'signal': 'BUY_PE', 'mode': 'scout'}
        
        return None

    def check_rumbling_entry(self, df, idx):
        """
        Rumbling Mode: MACD Trend Following (ONLY when trending!)
        """
        row = df.iloc[idx]
        close = row['index_close']
        ema21 = row['ema21']
        hist = row['macd_hist']
        prev1_hist = df['macd_hist'].iloc[idx - 1]
        choppiness = row['choppiness']
        
        # 🔥 CHOPPINESS FILTER FOR RUMBLING ONLY!
        if choppiness >= self.RUMBLING_CHOPPINESS_THRESHOLD:
            return None  # Don't take trend trades in choppy conditions
        
        # MACD momentum conditions
        macd_bullish = hist > 0 and hist > prev1_hist
        macd_bearish = hist < 0 and hist < prev1_hist
        
        # BUY_CE: Bullish momentum in trending market
        if close > ema21 and macd_bullish:
            return {'signal': 'BUY_CE', 'mode': 'rumbling'}
        
        # BUY_PE: Bearish momentum in trending market
        if close < ema21 and macd_bearish:
            return {'signal': 'BUY_PE', 'mode': 'rumbling'}
        
        return None

    def calculate_entry_levels(self, mode, side, entry_price, option_atr):
        """
        Calculate entry levels based on mode.
        """
        if mode == 'scout':
            sl = round(entry_price - self.SCOUT_SL_MULTIPLIER * option_atr, 2)
            tp1 = entry_price + self.SCOUT_TP1_POINTS
            return {'sl': sl, 'tp1': tp1}
        elif mode == 'rumbling':
            sl = round(entry_price - self.RUMBLING_SL_MULTIPLIER * option_atr, 2)
            tp1 = None
            return {'sl': sl, 'tp1': tp1}
        
        # Fallback
        sl = round(entry_price - 1.5 * option_atr, 2)
        return {'sl': sl, 'tp1': entry_price + 10}

    def check_exit_conditions(self, position, nifty_row, option_candle):
        """
        Check exit conditions with ATR-based trailing for both modes.
        """
        mode = position['mode']
        side = position['side']
        option_high = option_candle['high']
        option_close = option_candle['close']
        
        # Unpack nifty data
        nifty_close = nifty_row['index_close']
        ema21 = nifty_row['ema21']
        macd_hist = nifty_row['macd_hist']
        
        # Get BB for scout mode
        if mode == 'scout':
            bb_middle = nifty_row['bb_middle']
        
        # Update highest price reached
        if 'highest' not in position:
            position['highest'] = option_high
        else:
            position['highest'] = max(position['highest'], option_high)
        
        # Get option ATR
        option_atr = position.get('option_atr', 20)
        
        exit_reason, exit_price = None, None
        
        # --- SCOUT MODE EXIT LOGIC ---
        if mode == 'scout':
            # Check TP1 hit
            if not position.get('tp1_hit', False) and option_high >= position['tp1']:
                position['tp1_hit'] = True
                print(f"SCOUT MODE: TP1 Hit! ATR Trailing activated!")
            
            # ATR-based trailing after TP1
            if position.get('tp1_hit', False):
                trail_step = max(
                    self.SCOUT_MIN_TRAIL_POINTS,
                    self.SCOUT_TRAIL_ATR_MULTIPLIER * option_atr
                )
                new_sl = round(position['highest'] - trail_step, 2)
                if new_sl > position['sl']:
                    position['sl'] = new_sl
            
            # Mean reversion exit
            if side == 'BUY_CE' and nifty_close >= bb_middle:
                exit_reason, exit_price = "Mean Reversion Target", option_close
            elif side == 'BUY_PE' and nifty_close <= bb_middle:
                exit_reason, exit_price = "Mean Reversion Target", option_close
            
            # SL hit
            if not exit_reason and option_close <= position['sl']:
                exit_reason, exit_price = "SL Hit", position['sl']
        
        # --- RUMBLING MODE EXIT LOGIC ---
        elif mode == 'rumbling':
            # Breakeven trigger
            if not position.get('breakeven_activated', False):
                if option_high >= (position['entry_price'] + self.RUMBLING_BREAKEVEN_TRIGGER_POINTS):
                    position['breakeven_activated'] = True
                    position['sl'] = position['entry_price']
                    print(f"RUMBLING MODE: Breakeven activated!")
            
            # ATR-based trailing after breakeven
            if position.get('breakeven_activated', False):
                trail_step = max(
                    self.RUMBLING_MIN_TRAIL_POINTS,
                    self.RUMBLING_TRAIL_ATR_MULTIPLIER * option_atr
                )
                new_sl = round(position['highest'] - trail_step, 2)
                if new_sl > position['sl']:
                    position['sl'] = new_sl
            
            # SL hit
            if option_close <= position['sl']:
                exit_reason, exit_price = "SL Hit", position['sl']
            
            # Trend reversal exit (after breakeven)
            elif position.get('breakeven_activated', False):
                if side == 'BUY_CE' and (nifty_close < ema21 or macd_hist < 0):
                    exit_reason, exit_price = "Trend Reversal", option_close
                elif side == 'BUY_PE' and (nifty_close > ema21 or macd_hist > 0):
                    exit_reason, exit_price = "Trend Reversal", option_close
        
        # EOD exit (both modes)
        if not exit_reason and self.check_eod_exit(nifty_row['datetime'].time()):
            exit_reason, exit_price = "EOD Exit", option_close
        
        return exit_reason, exit_price
    
    def check_eod_exit(self, current_time):
        return current_time >= self.EOD_EXIT_TIME

    def calculate_pnl(self, side, entry_price, exit_price):
        pnl_points = exit_price - entry_price
        pnl_inr = pnl_points * self.LOT_SIZE
        return {'pnl_points': round(pnl_points, 2), 'pnl_inr': round(pnl_inr, 2)}