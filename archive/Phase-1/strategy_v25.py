from indicators import EMA, ATR, MACD, choppiness_index
from datetime import datetime
import os

from trader_config import LOT_SIZE, SL_MULTIPLIER

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
    choppiness = row['choppiness']
    rng = high - low
    ce_strength = (close - low) / rng if rng > 0 else 0
    pe_strength = (high - close) / rng if rng > 0 else 0
    # BUY_CE
    if time(9, 30) <= t <= time(15, 15):
        hist_rising = hist > prev1 > prev2
        if hist_rising and close > ema21 and choppiness < 55:
            return "BUY_CE"
        # SELL_PE
        hist_falling = hist < prev1 < prev2
        if (
            hist_falling and
            close < ema21 
            and choppiness < 55
        ):
            print(f"[ENTRY SIGNAL] SELL_PE {row['datetime']} | macd={macd:.3f} signal={signal:.3f} hist={hist:.3f} atr={atr:.2f}")
            return "SELL_PE"
    return None
#Trader Baddu:D
import pandas as pd
import numpy as np
from datetime import time

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
                                sl=round(close - SL_MULTIPLIER*atr, 2),  # initial SL
                                initial_sl=round(close - SL_MULTIPLIER*atr, 2),
                                tp1=close + 15, tp1_hit=False,
                                highest=close, sl_trail_count=0)
            elif signal_entry == "SELL_PE":
                position = dict(side="SELL_PE", entry_time=dt, entry_price=close,
                                sl=round(close + SL_MULTIPLIER*atr, 2),  # initial SL
                                initial_sl=round(close + SL_MULTIPLIER*atr, 2),
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
                    trail_step = max(10, 0.2 * atr)
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
                    trail_step = max(10, 0.2 * atr)
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
            

    # === Save Trade Log ===
    trade_rows, pnl = [], []
    for tr in trades:
        et, side, entry, xt, xp, reason, sl_val = tr
        pnl_pts = (xp - entry) if side == "BUY_CE" else (entry - xp)
        pnl_inr = pnl_pts * LOT_SIZE
        pnl.append(pnl_inr)
        trade_rows.append([
            et, side, entry, xt, xp, reason,
            sl_val,  # new column
            round(pnl_pts, 2), round(pnl_inr, 2)
        ])

    os.makedirs("trade_logs", exist_ok=True)
    trade_log_filename = os.path.join("trade_logs", f"V25Trade_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    pd.DataFrame(trade_rows, columns=[
        "EntryTime", "Side", "EntryPrice", "ExitTime", "ExitPrice", "Reason",
        "Exit_SL_Value",  # new column
        "PnL_Points", "PnL_INR"
    ]).to_csv(trade_log_filename, index=False)

    print("\n=== SUMMARY ===")
    print(f"Total Trades: {len(trades)}")
    print(f"Winrate: {(np.array(pnl) > 0).mean() * 100:.2f}%")
    print(f"PnL: ₹{sum(pnl):.2f}")



def run_backtest(data_path="nifty_5min_last_month.csv"):
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['ema21'] = EMA(df['close'], 21)
    df['macd'], df['macd_signal'], df['macd_hist'] = MACD(df['close'])
    df['atr'] = ATR(df)
    df['choppiness'] = choppiness_index(df)
    return backtest(df)