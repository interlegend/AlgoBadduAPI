#Trader Baddu:D
# PAPER TRADER for Strategy V25 (TradeHull, Fusion)
import os
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dtime

from data_fetcher import get_nifty_ohlc, get_option_ohlc, set_tsl, get_nifty_spot_price
from strategy_v25 import EMA, MACD, ATR, check_entry
from order_manager import get_atm_option_symbols
from config import LOT_SIZE, CLIENT_ID, ACCESS_TOKEN
from Dhan_Tradehull import Tradehull

# ----------------------
# Global configuration
# ----------------------
DEBUG = os.getenv("DEBUG", "0") == "1"
IST = pytz.timezone("Asia/Kolkata")
SESSION_START = dtime(9, 30)
SESSION_END = dtime(15, 25)
PAPER_LOG_FILE = "trade_logs/PaperTrade.csv"

# ----------------------
# Bootstrap Tradehull with preflight (fixes Invalid Token DH-906 early)
# ----------------------
try:
    print(f"[DEBUG] Initializing Tradehull with CLIENT_ID: {CLIENT_ID}, ACCESS_TOKEN: {ACCESS_TOKEN[:5]}...hidden")
    tsl = Tradehull(ClientCode=CLIENT_ID, token_id=ACCESS_TOKEN)
    set_tsl(tsl)  # set_tsl includes get_fund_limits preflight; will raise if token invalid
    print("[DEBUG] Tradehull client initialized and authenticated.")
except Exception as e:
    print(f"[FATAL] Could not init TradeHull client (token/auth): {e}")
    raise

# ----------------------
# Paper trade logging
# ----------------------
trade_memory = []

def log_paper_trade(entry, exit_time, exit_price, reason, lot_size=LOT_SIZE):
    """Append a trade row to CSV and in-memory for summary."""
    pnl_points = (exit_price - entry["entry_price"]) if entry["side"] == "BUY_CE" else (entry["entry_price"] - exit_price)
    pnl_inr = pnl_points * lot_size
    row = {
        "EntryTime": entry["entry_time"],
        "Side": entry["side"],
        "EntryPrice": float(entry["entry_price"]),
        "ExitTime": exit_time,
        "ExitPrice": float(exit_price),
        "Reason": reason,
        "PnL_Points": round(pnl_points, 2),
        "PnL_INR": round(pnl_inr, 2),
    }
    os.makedirs(os.path.dirname(PAPER_LOG_FILE), exist_ok=True)
    header = not os.path.exists(PAPER_LOG_FILE)
    pd.DataFrame([row]).to_csv(PAPER_LOG_FILE, mode="a", header=header, index=False)
    trade_memory.append(row)
    print(f"[PAPER LOG] {row}")

def print_summary():
    if not trade_memory:
        print("[SUMMARY] No trades taken")
        return
    df = pd.DataFrame(trade_memory)
    total = len(df)
    wins = (df["PnL_INR"] > 0).sum()
    winrate = (wins / total) * 100 if total else 0.0
    pnl_total = df["PnL_INR"].sum()
    print("\n=== PAPER TRADING SUMMARY ===")
    print(f"Total Trades: {total}")
    print(f"Winrate: {winrate:.2f}%")
    print(f"Net PnL: {pnl_total:.2f}")
    print("================================")

# ----------------------
# Helper: add indicators safely
# ----------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute EMA21, MACD, ATR with safe fallbacks."""
    df = df.copy()
    df["ema21"] = EMA(df["close"], 21)
    macd_tuple = MACD(df["close"])
    if isinstance(macd_tuple, tuple) and len(macd_tuple) >= 3:
        df["macd"], df["macd_signal"], df["macd_hist"] = macd_tuple
    else:
        df["macd"] = df["macd_signal"] = df["macd_hist"] = np.nan
    df["atr"] = ATR(df)
    return df

# ----------------------
# Main
# ----------------------
def main():
    print("[INFO] Starting PAPER TRADER for Strategy V25 (TradeHull, Fusion)")
    position = None

    # 1) Fetch NIFTY to get spot and reference datetime
    try:
        spot = get_nifty_spot_price()
        test_date = datetime.now(IST)  # Use current time for test_date
        print(f"[INFO] NIFTY spot={spot} at {test_date}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch NIFTY spot price: {e}. Aborting.")
        return

    # 2) Resolve ATM CE/PE SEM_TRADING_SYMBOLs
    try:
        atm = get_atm_option_symbols(base_symbol="NIFTY", spot=spot, when_dt=test_date)
        ce_symbol, pe_symbol = atm["CE_symbol"], atm["PE_symbol"]
        print(f"[INFO] ATM Symbols: CE={ce_symbol} | PE={pe_symbol}")
        # Debug: Show resolved contract row from instrument master
        print(f"[DEBUG] ATM Option Metadata: {atm}")
        # Deep debug: print full instrument row for CE symbol
        instrument_csv_path = None
        import glob, os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        primary_pattern = os.path.join(project_root, 'Dependencies', 'all_instrument*.csv')
        files = sorted(glob.glob(primary_pattern, recursive=False), key=os.path.getmtime)
        if files:
            instrument_csv_path = files[-1]
        if instrument_csv_path:
            import pandas as pd
            inst_df = pd.read_csv(instrument_csv_path, low_memory=False)
            ce_row = inst_df[inst_df['SEM_TRADING_SYMBOL'].astype(str).str.upper() == str(ce_symbol).upper()]
            if not ce_row.empty:
                print("[DEBUG] Full instrument row for CE symbol:")
                print(ce_row.iloc[0].to_dict())
    except Exception as e:
        print(f"[ERROR] Failed to resolve ATM symbols: {e}")
        return

    # 3) Fetch CE/PE OHLC (5m); data_fetcherperp already enforces timeframe + tz + column checks
    ce_ohlc = get_option_ohlc(str(ce_symbol), interval=5, exchange='NFO')
    pe_ohlc = get_option_ohlc(str(pe_symbol), interval=5, exchange='NFO')

    if ce_ohlc.empty or pe_ohlc.empty:
        print("[ERROR] One or both option OHLC datasets are empty. Aborting.")
        return

    # Normalize datetimes
    for df in (ce_ohlc, pe_ohlc):
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    ce_ohlc = ce_ohlc.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    pe_ohlc = pe_ohlc.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

    # 4) Add indicators
    ce_ohlc = add_indicators(ce_ohlc)
    pe_ohlc = add_indicators(pe_ohlc)

    # 5) Filter to session window
    ce_ohlc = ce_ohlc[(ce_ohlc["datetime"].dt.time >= SESSION_START) & (ce_ohlc["datetime"].dt.time <= SESSION_END)].copy().reset_index(drop=True)
    pe_ohlc = pe_ohlc[(pe_ohlc["datetime"].dt.time >= SESSION_START) & (pe_ohlc["datetime"].dt.time <= SESSION_END)].copy().reset_index(drop=True)

    if len(ce_ohlc) < 50 or len(pe_ohlc) < 50:
        print("[ERROR] Not enough bars after session filter (<50). Aborting.")
        return

    # 6) Main loop: synchronized CE/PE simulation with clear TP/SL/EOD exits
    for side, opt_df in [("BUY_CE", ce_ohlc), ("SELL_PE", pe_ohlc)]:
        open_trade = None
        entry_idx = None

        for i in range(2, len(opt_df)):
            row = opt_df.iloc[i]
            dt = row["datetime"]
            close = float(row["close"])
            signal = check_entry(opt_df, i)

            # Entry logic
            if open_trade is None and signal == side:
                open_trade = {
                    "side": side,
                    "entry_time": dt,
                    "entry_price": close,
                }
                entry_idx = i
                print(f"[ENTRY] {side} at {dt} price={close}")
                continue

            # Manage open trade
            if open_trade is not None:
                atr_val = float(opt_df.at[i, "atr"]) if not pd.isna(opt_df.at[i, "atr"]) else 0.0

                # Basic SL/TP based on direction; tweak as per strat_v25 rules if needed
                if side == "BUY_CE":
                    sl_val = open_trade["entry_price"] - 1.5 * atr_val
                    tp_val = open_trade["entry_price"] + 15
                    sl_hit = close <= sl_val
                    tp_hit = close >= tp_val
                else:  # SELL_PE
                    sl_val = open_trade["entry_price"] + 1.5 * atr_val
                    tp_val = open_trade["entry_price"] - 15
                    sl_hit = close >= sl_val
                    tp_hit = close <= tp_val

                # Stop Loss hit
                if sl_hit:
                    log_paper_trade(open_trade, dt, sl_val, "SL Hit", LOT_SIZE)
                    print(f"[EXIT] SL Hit {side} at {dt} exit={sl_val}")
                    open_trade = None
                    entry_idx = None
                    continue

                # Take Profit hit
                if tp_hit:
                    log_paper_trade(open_trade, dt, tp_val, "TP Hit", LOT_SIZE)
                    print(f"[EXIT] TP Hit {side} at {dt} exit={tp_val}")
                    open_trade = None
                    entry_idx = None
                    continue

                # End-of-day exit
                if dt.time() >= SESSION_END:
                    log_paper_trade(open_trade, dt, close, "EOD EXIT", LOT_SIZE)
                    print(f"[EXIT] EOD {side} at {dt} exit={close}")
                    open_trade = None
                    entry_idx = None
                    continue

    print_summary()

if __name__ == "__main__":
    main()