# === Entry Signal Function ===
def check_entry(df, i):
    """
    df: DataFrame with ['datetime','open','high','low','close','ema21','macd','macd_signal','macd_hist','atr']
    i: index of the current candle
    Returns: "BUY_CE", "SELL_PE", or None
    """
    from datetime import time
    if i < 1:
        return None  # Not enough history for 2-bar logic
    row = df.iloc[i]
    t = row['datetime'].time()
    close = row['close']
    high = row['high']
    low = row['low']
    ema21 = row['ema21']
    atr = row['atr']
    macd = row['macd']
    signal = row['macd_signal']
    hist = row['macd_hist']
    prev1 = df['macd_hist'].iloc[i-1]
    prev2 = df['macd_hist'].iloc[i-2]
    rng = high - low
    ce_strength = (close - low) / rng if rng > 0 else 0
    pe_strength = (high - close) / rng if rng > 0 else 0
    # BUY_CE
    if time(9, 30) <= t <= time(15, 15):
        hist_rising = hist > prev1 > prev2
        if (
            hist_rising and
            (macd - signal) > 0.20 and
            close > ema21 and
            (atr / close) >= 0.00065

        ):
            print(f"[ENTRY SIGNAL] BUY_CE {row['datetime']} | macd={macd:.3f} signal={signal:.3f} hist={hist:.3f} atr={atr:.2f}")
            return "BUY_CE"
        # SELL_PE
        hist_falling = hist < prev1 < prev2
        if (
            hist_falling and
            (macd - signal) < -0.20 and
            close < ema21 and
            (atr / close) >= 0.00065
        ):
            print(f"[ENTRY SIGNAL] SELL_PE {row['datetime']} | macd={macd:.3f} signal={signal:.3f} hist={hist:.3f} atr={atr:.2f}")
            return "SELL_PE"
    return None
#Trader Baddu:D
import pandas as pd
import numpy as np
from datetime import time

# === Helper Functions ===
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def ATR(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def MACD(series, fast=12, slow=26, signal=9):
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = EMA(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

# === Backtest Engine ===
def backtest(data):
    trades = []
    position = None


    for i in range(35, len(data)):
        row = data.iloc[i]
        dt = row['datetime']
        t = dt.time()
        close = row['close']
        high = row['high']
        low = row['low']
        ema21 = row['ema21']
        atr = row['atr']
        macd = row['macd']
        signal = row['macd_signal']
        hist = row['macd_hist']

        # === Entry (strictly via check_entry) ===
        if not position:
            signal_entry = check_entry(data, i)
            if signal_entry == "BUY_CE":
                position = dict(side="BUY_CE", entry_time=dt, entry_price=close,
                                sl=round(close - 1.0*atr, 2),  # initial SL
                                initial_sl=round(close - 1.0*atr, 2),
                                tp1=close + 15, tp1_hit=False,
                                highest=close, sl_trail_count=0)
            elif signal_entry == "SELL_PE":
                position = dict(side="SELL_PE", entry_time=dt, entry_price=close,
                                sl=round(close + 1.0*atr, 2),  # initial SL
                                initial_sl=round(close + 1.0*atr, 2),
                                tp1=close - 15, tp1_hit=False,
                                lowest=low, sl_trail_count=0)

        # === Manage Trade ===
        if position:
            side = position['side']
            entry = position['entry_price']
            tp1 = position['tp1']

            # update highs/lows
            if side == "BUY_CE":
                position['highest'] = max(position['highest'], high)
            else:
                position['lowest'] = min(position['lowest'], low)

            # === Initial SL check (before TP1) ===
            if not position.get('tp1_hit', False):
                if side == "BUY_CE" and close <= position['initial_sl']:
                    print(f"[EXIT] BUY_CE {dt} Initial SL Hit @ {position['initial_sl']}")
                    trades.append((position['entry_time'], side, entry, dt, position['initial_sl'], "Initial SL Hit", position['initial_sl']))
                    position = None
                    continue
                elif side == "SELL_PE" and close >= position['initial_sl']:
                    print(f"[EXIT] SELL_PE {dt} Initial SL Hit @ {position['initial_sl']}")
                    trades.append((position['entry_time'], side, entry, dt, position['initial_sl'], "Initial SL Hit", position['initial_sl']))
                    position = None
                    continue

            # === TP1 lock logic and trailing (TP2 logic removed) ===
            if side == "BUY_CE":
                tp1 = entry + 15
                if not position.get('tp1_hit', False) and high >= tp1:
                    position['tp1_hit'] = True
                    position['sl'] = round(entry + 13, 2)
                    position['tp1_candle'] = dt
                    print(f"[TP1] BUY_CE {dt} tp1={tp1} locked_sl={position['sl']}")
            else:  # SELL_PE
                tp1 = entry - 15
                if not position.get('tp1_hit', False) and low <= tp1:
                    position['tp1_hit'] = True
                    position['sl'] = round(entry - 13, 2)
                    position['tp1_candle'] = dt
                    print(f"[TP1] SELL_PE {dt} tp1={tp1} locked_sl={position['sl']}")

            # === Exit Logic with trailing after TP1 (no TP2 logic) ===
            if side == "BUY_CE":
                # SL check
                if close <= position['sl']:
                    print(f"[EXIT] BUY_CE {dt} SL Hit @ {position['sl']}")
                    trades.append((position['entry_time'], side, entry, dt, position['sl'], "SL Hit", position['sl']))
                    position = None
                    continue

                # Trailing logic after TP1
                if position.get('tp1_hit', False):
                    trail_step = max(10, 0.3 * atr)
                    new_sl = round(max(position['sl'], position['highest'] - trail_step), 2)
                    if new_sl > position['sl']:
                        position['sl'] = new_sl
                        print(f"[TRAIL] BUY_CE {dt} new_sl={new_sl}")

                    # Fail-safe EMA/MACD exit
                    if close < ema21 or hist < 0:
                        print(f"[EXIT] BUY_CE {dt} MACD/EMA Exit @ {close}")
                        trades.append((position['entry_time'], side, entry, dt, close, "MACD/EMA Exit", position['sl']))
                        position = None
                        continue

            else:  # SELL_PE
                if close >= position['sl']:
                    print(f"[EXIT] SELL_PE {dt} SL Hit @ {position['sl']}")
                    trades.append((position['entry_time'], side, entry, dt, position['sl'], "SL Hit", position['sl']))
                    position = None
                    continue

                if position.get('tp1_hit', False):
                    trail_step = max(10, 0.3 * atr)
                    new_sl = round(min(position['sl'], position['lowest'] + trail_step), 2)
                    if new_sl < position['sl']:
                        position['sl'] = new_sl
                        print(f"[TRAIL] SELL_PE {dt} new_sl={new_sl}")

                    if close > ema21 or hist > 0:
                        print(f"[EXIT] SELL_PE {dt} MACD/EMA Exit @ {close}")
                        trades.append((position['entry_time'], side, entry, dt, close, "MACD/EMA Exit", position['sl']))
                        position = None
                        continue

            # === EOD Exit (unchanged) ===
            if t >= time(15, 25):
                print(f"[EXIT] {side} {dt} EOD Exit @ {close}")
                trades.append((position['entry_time'], side, entry, dt, close, "EOD Exit", position['sl']))
                position = None
                continue
            
    return trades



def run_backtest(data_path="nifty_5min_last_month.csv"):
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['ema21'] = EMA(df['close'], 21)
    df['macd'], df['macd_signal'], df['macd_hist'] = MACD(df['close'])
    df['atr'] = ATR(df)
    return backtest(df)