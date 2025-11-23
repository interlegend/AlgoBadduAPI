import os
import json
import pandas as pd
from datetime import datetime, timedelta
from fyers_apiv3 import fyersModel

# Load access token from token.json
def load_token():
    token_file = "token.json"
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            try:
                return json.load(f)
            except:
                print("❌ Invalid token file.")
    return None

# Build FyersModel client using token
def build_fyers_client():
    tokens = load_token()
    if not tokens or "access_token" not in tokens:
        raise Exception("❌ Token not found. Please run auth.py first.")

    # Make sure client_id matches your APP ID
    client_id = "77Z3CHKI1N-100"  # 🔁 Use YOUR working App ID here
    access_token = tokens["access_token"]

    fyers = fyersModel.FyersModel(
        client_id=client_id,
        token=access_token,
        log_path=""  # Optional: set path to save logs
    )
    return fyers

# Fetch OHLC candles using fyers.history
def get_ohlc(symbol="NSE:NIFTY50-INDEX", resolution="1", days_back=30):
    fyers = build_fyers_client()

    # Yesterday at 3:30 PM IST
    include_today = False  # 👈 Set to False to exclude today

    end_dt = datetime.now().astimezone().replace(hour=15, minute=30, second=0, microsecond=0)
    if not include_today:
        end_dt -= timedelta(days=1)


    # Start date = 1 month ago
    start_dt = end_dt - timedelta(days=days_back)

    # Convert to epoch timestamps (UTC)
    start_epoch = int(start_dt.timestamp())
    end_epoch = int(end_dt.timestamp())

    print(f"🕒 Fetching from {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%Y-%m-%d %H:%M')} IST")

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": 0,  # epoch
        "range_from": start_epoch,
        "range_to": end_epoch,
        "cont_flag": 1
    }

    response = fyers.history(params)

    if response.get("s") != "ok":
        print("❌ Error fetching data:", response)
        return None

    candles = response.get("candles", [])
    if not candles:
        print("⚠️ No data returned.")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
    df = df[["datetime", "open", "high", "low", "close", "volume"]]

    print(f"✅ Fetched {len(df)} candles.")
    df.to_csv("nifty_5min_last_month.csv", index=False)
    
    # Also save raw response
    with open("fetched_candles.json", "w") as f:
        json.dump(response, f, indent=2)

    return df


# Example usage
if __name__ == "__main__":
    df = get_ohlc()
