import os
import pandas as pd
from datetime import datetime
from data.data_fetcher import get_recent_ohlc_window
from data.data_analyzer import add_bbands, add_adx, basic_summary

# --- Configuration ---
symbol = "NSE:NIFTY50-INDEX"
resolution = "5"  # 5-minute candles
minutes_back = 180  # Fetch last 3 hours

# --- Fetch recent OHLC data ---
print("📈 Fetching recent OHLC data...")
df = get_recent_ohlc_window(symbol=symbol, resolution=resolution, minutes_back=minutes_back)

# --- Analyze data ---
print("🔍 Adding indicators...")
df = add_bbands(df)
df = add_adx(df)

# --- Summary ---
print("📊 Data Summary:")
basic_summary(df)

# --- Save to CSV ---
output_dir = "out"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "nifty5m.csv")
df.to_csv(output_file, index=False)
print(f"✅ Data saved to {output_file}")