
import sys
import os
import pandas as pd
import numpy as np
import requests
import urllib.parse
from datetime import datetime, timedelta
import logging
import pandas_ta as ta  # Using pandas_ta for its reliable ATR calculation

# Add path for imports
sys.path.append(os.path.join(os.getcwd(), 'Algo Baddu Trading API', 'Phase-3'))
from config_live import UPSTOX_ACCESS_TOKEN
from commodity_selector import CommodityKeySelector

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def get_natural_gas_data():
    """Fetches a robust dataset for Natural Gas."""
    print("📥 Fetching NATURALGAS Data...")
    selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
    key, _, _ = selector.get_current_future("NATURALGAS")
    
    if not key:
        print("❌ No Active Contract Found")
        return None

    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=10) # Using 10 days for more stability
    
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    encoded_key = urllib.parse.quote(key, safe='')
    
    candles = []
    # Historical
    url_hist = f"https://api.upstox.com/v3/historical-candle/{encoded_key}/minutes/5/{to_date}/{from_date}"
    try:
        res = requests.get(url_hist, headers=headers, timeout=20)
        if res.status_code == 200:
            candles.extend(res.json().get("data", {}).get("candles", []))
    except Exception as e:
        print(f"Error fetching historical: {e}")

    # Intraday
    url_intra = f"https://api.upstox.com/v3/historical-candle/intraday/{encoded_key}/minutes/5"
    try:
        res = requests.get(url_intra, headers=headers, timeout=20)
        if res.status_code == 200:
            candles.extend(res.json().get("data", {}).get("candles", []))
    except Exception as e:
        print(f"Error fetching intraday: {e}")

    # Process and deduplicate
    parsed = []
    seen_timestamps = set()
    for c in candles:
        ts_str = c[0]
        if ts_str in seen_timestamps: continue
        seen_timestamps.add(ts_str)
        parsed.append({
            'timestamp': pd.to_datetime(ts_str),
            'open': float(c[1]), 'high': float(c[2]), 'low': float(c[3]), 'close': float(c[4])
        })
    
    parsed.sort(key=lambda x: x['timestamp'])
    df = pd.DataFrame(parsed).set_index('timestamp') # Set timestamp as index for easier slicing
    print(f"✅ Loaded {len(df)} unique candles for NATURALGAS.")
    return df

def calculate_chop_A_sum_tr(df, period=14):
    """Method A (Current): Using Sum of True Range."""
    high, low, close = df['high'], df['low'], df['close']
    
    # Calculate True Range manually
    tr = ta.true_range(high, low, close)
    
    sum_tr = tr.rolling(period).sum()
    max_hi = high.rolling(period).max()
    min_lo = low.rolling(period).min()
    
    range_diff = max_hi - min_lo
    range_diff = range_diff.replace(0, np.nan)
    
    chop = 100 * np.log10(sum_tr / range_diff) / np.log10(period)
    return chop

def calculate_chop_B_atr(df, period=14):
    """Method B (Alternative): Using ATR * Period, which is a smoothed sum."""
    high, low, close = df['high'], df['low'], df['close']
    
    # Use pandas_ta for a reliable, standard ATR calculation
    atr = ta.atr(high, low, close, length=period)
    
    # The formula uses SUM(TR), which ATR approximates with smoothing.
    # So, ATR * period is a "smoothed" SUM(TR).
    smoothed_sum_tr = atr * period
    
    max_hi = high.rolling(period).max()
    min_lo = low.rolling(period).min()
    
    range_diff = max_hi - min_lo
    range_diff = range_diff.replace(0, np.nan)
    
    chop = 100 * np.log10(smoothed_sum_tr / range_diff) / np.log10(period)
    return chop

def main():
    df = get_natural_gas_data()
    if df is None or df.empty: return

    # Calculate both methods
    df['CHOP_A'] = calculate_chop_A_sum_tr(df)
    df['CHOP_B'] = calculate_chop_B_atr(df)
    
    # Get last 5 rows for better context
    tail = df.tail(5)
    
    print("\n" + "="*80)
    print("📊 NATURAL GAS CHOPPINESS (14) DEEP DIVE")
    print("="*80)
    print("Method A: Sum of True Range (Current Logic)")
    print("Method B: ATR-based Smoothed Sum (Alternative Logic)")
    print("-"*80)
    
    for timestamp, row in tail.iterrows():
        print(f"Time: {timestamp.strftime('%H:%M')} | Close: {row['close']:.2f} | CHOP_A: {row['CHOP_A']:.2f} | CHOP_B: {row['CHOP_B']:.2f}")
        
    print("="*80)
    print("\n👉 COMMANDER, please compare Method A vs Method B with your broker chart.")
    print("   Which one is closer to the truth for Natural Gas?")

if __name__ == "__main__":
    main()
