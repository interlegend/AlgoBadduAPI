"""
🔥 FINAL RUN_ALL.PY – CLEAN VERSION
1. Uses saved token from token.json
2. Fetches last 1 month of 5-min Nifty candles
3. Skips token refresh (done manually via auth.py)
4. Shows output and saves to CSV/JSON
5. Tells you if token is expired or invalid
"""

from data.data_fetcher import get_ohlc
import traceback

print("📈 Starting OHLC candle fetch using saved token...")

try:
    df = get_ohlc(
        symbol="NSE:NIFTY50-INDEX",
        resolution="5",
        days_back=30
    )

    if df is not None:
        print("✅ Candle data fetched successfully!")
        print(df.tail())
    else:
        print("⚠️ No data returned. Check time window or symbol.")

except Exception as e:
    print("❌ ERROR while fetching data.")
    print("⚠️ This might mean your access token is expired or invalid.")
    print("👉 Run auth.py manually to get a new token.")
    print("📄 Full traceback:")
    traceback.print_exc()
