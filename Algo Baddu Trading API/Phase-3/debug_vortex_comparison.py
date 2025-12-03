
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

def get_crude_data():
    """Fetch 500+ candles for Crude Oil"""
    print("📥 Fetching Crude Oil Data...")
    selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
    key, _, _ = selector.get_current_future("CRUDEOIL")
    
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
    print(f"✅ Loaded {len(df)} candles.")
    return df

def calculate_vortex_method_A_rolling_sum(df, period=34):
    """Current Implementation: Simple Rolling Sum"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # VM
    vm_plus = np.abs(high - low.shift(1))
    vm_minus = np.abs(low - high.shift(1))
    
    # Sum
    sum_tr = tr.rolling(period).sum()
    sum_vm_plus = vm_plus.rolling(period).sum()
    sum_vm_minus = vm_minus.rolling(period).sum()
    
    vi_plus = sum_vm_plus / sum_tr
    vi_minus = sum_vm_minus / sum_tr
    return vi_plus, vi_minus

def calculate_vortex_method_B_smoothed(df, period=34):
    """Alternative: Smoothed Sum (RMA/Wilders) - Used by some platforms"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # VM
    vm_plus = np.abs(high - low.shift(1))
    vm_minus = np.abs(low - high.shift(1))
    
    # Helper for RMA (Wilders Smoothing)
    # RMA is equivalent to EWM with alpha = 1/period
    # Pandas ewm(alpha=1/period, adjust=False).mean() is close, but we need SUM analog
    # RMA(x, n) = (Prev_RMA * (n-1) + Curr_x) / n
    # But standard Vortex is SUM based. Some versions smooth the TR and VM.
    
    # Trying standard Pandas TA 'vortex' logic again but with drift check
    # Actually, let's try the "Talib" style if possible, but manual.
    # Let's just try a simple 'rolling sum' but with a shift? No.
    
    # Let's try the method where they don't use 'Shift' for VM but use High - Low? No that's wrong.
    
    # Let's try "TradingView specific" implementation which is basically Method A.
    # If Method A is correct, then the issue is data. 
    # But let's simulate a "Smoothed" version just in case.
    
    return calculate_vortex_method_A_rolling_sum(df, period) # Placeholder if no distinct method B found yet

def main():
    df = get_crude_data()
    if df is None or df.empty: return

    # Calculate
    vi_plus_A, vi_minus_A = calculate_vortex_method_A_rolling_sum(df, 34)
    
    # Get last 3 rows
    tail = df.tail(3).copy()
    tail['VI+_A'] = vi_plus_A.tail(3)
    tail['VI-_A'] = vi_minus_A.tail(3)
    
    print("\n📊 COMPARISON MATRIX (Last 3 Candles)")
    print("="*80)
    for i, row in tail.iterrows():
        print(f"Time: {row['timestamp'].strftime('%H:%M')} | Close: {row['close']} | VI+ (34): {row['VI+_A']:.4f} | VI- (34): {row['VI-_A']:.4f}")
    print("="*80)
    print("\n👉 COMPARE THESE VALUES WITH YOUR BROKER CHART (CRUDE OIL 5m).")
    print("   If they match ~98%, the math is good. If not, it's the data feed.")

if __name__ == "__main__":
    main()
