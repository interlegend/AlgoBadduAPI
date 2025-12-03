
import sys
import os
import pandas as pd
import numpy as np
import requests
import urllib.parse
from datetime import datetime, timedelta
import logging

# Add path for imports
sys.path.append(os.path.join(os.getcwd(), 'Algo Baddu Trading API', 'Phase-3'))
from config_live import UPSTOX_ACCESS_TOKEN
from commodity_selector import CommodityKeySelector

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def get_commodity_data(asset_name):
    """Fetch 500+ candles for Asset"""
    print(f"📥 Fetching {asset_name} Data...")
    selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
    key, _, _ = selector.get_current_future(asset_name)
    
    if not key:
        print("❌ No Active Contract Found")
        return None

    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=5)
    
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    encoded_key = urllib.parse.quote(key, safe='')
    
    # Historical
    url_hist = f"https://api.upstox.com/v3/historical-candle/{encoded_key}/minutes/5/{to_date}/{from_date}"
    candles = []
    try:
        res = requests.get(url_hist, headers=headers)
        if res.status_code == 200:
            candles.extend(res.json().get("data", {}).get("candles", []))
    except Exception as e:
        print(f"Error fetching historical: {e}")

    # Intraday
    url_intra = f"https://api.upstox.com/v3/historical-candle/intraday/{encoded_key}/minutes/5"
    try:
        res = requests.get(url_intra, headers=headers)
        if res.status_code == 200:
            candles.extend(res.json().get("data", {}).get("candles", []))
    except Exception as e:
        print(f"Error fetching intraday: {e}")

    # Process
    parsed = []
    seen = set()
    for c in candles:
        ts = c[0]
        if ts in seen: continue
        seen.add(ts)
        parsed.append({
            'timestamp': pd.to_datetime(ts),
            'open': c[1], 'high': c[2], 'low': c[3], 'close': c[4]
        })
    
    parsed.sort(key=lambda x: x['timestamp'])
    df = pd.DataFrame(parsed)
    print(f"✅ Loaded {len(df)} candles for {asset_name}.")
    return df

def calculate_choppiness(df, period=14):
    """Manual Choppiness Index Calculation"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Sum TR
    sum_tr = tr.rolling(period).sum()
    
    # Max High - Min Low
    max_hi = high.rolling(period).max()
    min_lo = low.rolling(period).min()
    
    range_diff = max_hi - min_lo
    range_diff = range_diff.replace(0, np.nan)
    
    # Formula
    x = sum_tr / range_diff
    chop = 100 * np.log10(x) / np.log10(period)
    
    return chop

def main():
    assets = ["CRUDEOIL", "NATURALGAS"]
    
    for asset in assets:
        print(f"\n>>> ANALYZING {asset} <<<")
        df = get_commodity_data(asset)
        if df is None or df.empty: continue

        # Calculate Chop
        chop = calculate_choppiness(df, 14)
        
        # Get last 3 rows
        tail = df.tail(3).copy()
        tail['CHOP (14)'] = chop.tail(3)
        
        print(f"\n📊 {asset} CHOPPINESS MATRIX (Last 3 Candles)")
        print("="*60)
        for i, row in tail.iterrows():
            print(f"Time: {row['timestamp'].strftime('%H:%M')} | Close: {row['close']} | CHOP (14): {row['CHOP (14)']:.2f}")
        print("="*60)

if __name__ == "__main__":
    main()
