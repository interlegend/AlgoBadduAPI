"""
Collect NIFTY ATM Option Candle Data (5MIN) from Dhan API
- Uses dhanhq SDK-style payload (correct fields, formats)
- Gets NIFTY spot candles (securityId=13, IDX, INDEX)
- Resolves nearest 4 expiries and downloads ATM CE/PE option candles
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN
from order_manager import get_nifty_security_id, fetch_expiry_list, get_atm_option_symbol

# === Config ===
SAVE_DIR = "data/options"
INTERVAL = 5   # integer, minutes
MAX_EXPIRIES = 4
DAYS_BACK = 30
DRY_RUN = False

os.makedirs(SAVE_DIR, exist_ok=True)
IST = pytz.timezone("Asia/Kolkata")

INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
HEADERS = {
    "access-token": DHAN_ACCESS_TOKEN,
    "client-id": DHAN_CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# === Candle Fetcher ===
def fetch_intraday(security_id, exchange_segment, instrument, from_date, to_date, interval=INTERVAL, expiry_code=0):
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": exchange_segment,
        "instrument": instrument,
        "fromDate": from_date,
        "toDate": to_date,
        "interval": interval,
    }
    if instrument == "OPTIDX":
        payload["expiryCode"] = expiry_code

    backoff = 2.0
    for attempt in range(4):
        try:
            resp = requests.post(INTRADAY_URL, headers=HEADERS, json=payload, timeout=15)
            if resp.status_code == 200:
                js = resp.json()
                data = js.get("data", [])
                if not data:
                    print(f"[WARN] No candles returned for {security_id}")
                    return None
                df = pd.DataFrame(data)
                if "timestamp" not in df.columns:
                    print(f"[ERROR] Unexpected data format: {df.head()}")
                    return None
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
                df = df[["datetime", "open", "high", "low", "close", "volume"]]
                return df.sort_values("datetime").reset_index(drop=True)
            elif resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", backoff))
                print(f"[RATE LIMIT] Waiting {wait}s before retry...")
                time.sleep(wait)
                backoff *= 2
            else:
                print(f"[ERROR] HTTP {resp.status_code}: {resp.text[:200]}")
                time.sleep(backoff)
                backoff *= 2
        except Exception as e:
            print(f"[EXCEPTION] {e}, attempt {attempt+1}")
            time.sleep(backoff)
            backoff *= 2
    print(f"[ERROR] Failed to fetch intraday for {security_id}")
    return None

# === Main ===
def main():
    print("[INFO] Starting improved NIFTY ATM Option Collector")

    nifty_id = get_nifty_security_id() or 13
    print(f"[NIFTY ID] Using SECURITY_ID = {nifty_id}")

    expiries = fetch_expiry_list(nifty_id)
    if not expiries:
        print("[ERROR] No expiries fetched from API.")
        return
    expiries = expiries[:MAX_EXPIRIES]
    print(f"[INFO] Target expiries: {expiries}")

    # Time window (last DAYS_BACK days, IST)
    to_date = datetime.now(IST).replace(hour=15, minute=30, second=0, microsecond=0)
    from_date = to_date - timedelta(days=DAYS_BACK)
    from_str = from_date.strftime("%Y-%m-%d %H:%M:%S")
    to_str = to_date.strftime("%Y-%m-%d %H:%M:%S")

    # Fetch NIFTY spot for ATM resolution
    print("[INFO] Fetching latest NIFTY spot candle...")
    nifty_df = fetch_intraday(
        security_id=nifty_id,
        exchange_segment="IDX",
        instrument="INDEX",
        from_date=from_str,
        to_date=to_str,
        interval=INTERVAL
    )
    if nifty_df is None or nifty_df.empty:
        print("[ERROR] Could not fetch NIFTY spot data")
        return
    spot_price = float(nifty_df.iloc[-1]["close"])
    print(f"[SUCCESS] NIFTY spot: {spot_price}")

    # Loop through expiries
    for expiry in expiries:
        print(f"\n[EXPIRY] Processing {expiry}")
        ce = get_atm_option_symbol(spot_price, "BUY_CE", expiry)
        pe = get_atm_option_symbol(spot_price, "SELL_PE", expiry)

        for opt in [ce, pe]:
            if not opt:
                continue
            fname = f"{opt['trading_symbol']}_{expiry}.csv"
            fpath = os.path.join(SAVE_DIR, fname)

            if DRY_RUN:
                print(f"[DRY RUN] Would fetch {fname}")
                continue

            print(f"[FETCH] {opt['trading_symbol']} ({opt['security_id']})")
            df_opt = fetch_intraday(
                security_id=opt["security_id"],
                exchange_segment="NSE_FNO",
                instrument="OPTIDX",
                from_date=from_str,
                to_date=to_str,
                interval=INTERVAL,
                expiry_code=0
            )
            if df_opt is None or df_opt.empty:
                print(f"[SKIP] No candles for {opt['trading_symbol']}")
                continue

            df_opt.to_csv(fpath, index=False)
            print(f"[SAVED] {fpath} ({len(df_opt)} rows)")

    print("\n[DONE] Option candle collection complete!")

if __name__ == "__main__":
    main()
