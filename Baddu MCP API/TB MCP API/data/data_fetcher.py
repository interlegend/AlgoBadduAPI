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
def get_ohlc(symbol="NSE:NIFTY50-INDEX", resolution="5", days_back=365):
    fyers = build_fyers_client()
    include_today = True
    end_dt = datetime.now().astimezone().replace(hour=15, minute=30, second=0, microsecond=0)
    if not include_today:
        end_dt -= timedelta(days=1)
    start_dt = end_dt - timedelta(days=days_back)

    # Fyers API allows max 100 days per intraday request
    max_chunk = 100
    chunk_start = start_dt
    all_chunks = []
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Output CSV")
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, "nifty_5min_last_year.csv")
    first_chunk = True

    # Remove old CSV if exists
    if os.path.exists(csv_file):
        os.remove(csv_file)

    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=max_chunk), end_dt)
        start_epoch = int(chunk_start.timestamp())
        end_epoch = int(chunk_end.timestamp())
        print(f"🕒 Fetching from {chunk_start.strftime('%Y-%m-%d %H:%M')} to {chunk_end.strftime('%Y-%m-%d %H:%M')} IST")
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": 0,
            "range_from": start_epoch,
            "range_to": end_epoch,
            "cont_flag": 1
        }
        response = fyers.history(params)
        if response.get("s") != "ok":
            print("❌ Error fetching data:", response)
            chunk_start = chunk_end
            continue
        candles = response.get("candles", [])
        if not candles:
            print("⚠️ No data returned.")
            chunk_start = chunk_end
            continue
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s").dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        all_chunks.append(df)
        # Optional: append to CSV after each chunk
        df.to_csv(csv_file, mode="a", header=first_chunk, index=False)
        first_chunk = False
        chunk_start = chunk_end
    if not all_chunks:
        print("❌ No data fetched for any chunk.")
        return None
    final_df = pd.concat(all_chunks, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=["datetime"]).reset_index(drop=True)
    final_df.to_csv(csv_file, index=False)
    print(f"✅ Final dataset: {len(final_df)} candles from {final_df['datetime'].iloc[0]} to {final_df['datetime'].iloc[-1]}")
    # Save raw response of last chunk for inspection
    with open("fetched_candles.json", "w") as f:
        json.dump(response, f, indent=2)
    return final_df


# Example usage
if __name__ == "__main__":
    df = get_ohlc()
