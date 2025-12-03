
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

def get_natural_gas_data():
    """Fetches a robust dataset for Natural Gas."""
    print("📥 Fetching NATURALGAS Data...")
    selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
    key, _, _ = selector.get_current_future("NATURALGAS")
    
    if not key:
        print("❌ No Active Contract Found")
        return None

    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=10)
    
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
    df = pd.DataFrame(parsed).set_index('timestamp')
    print(f"✅ Loaded {len(df)} unique candles for NATURALGAS.")
    return df

def calculate_vortex_components(df, period=34):
    """Calculates VI+ and VI- along with their raw components for debugging."""
    high, low, close = df['high'], df['low'], df['close']
    
    # --- Component Calculation ---
    df['prev_low'] = low.shift(1)
    df['prev_high'] = high.shift(1)
    df['vm_plus'] = np.abs(high - df['prev_low'])
    df['vm_minus'] = np.abs(low - df['prev_high'])
    
    # --- True Range ---
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # --- Summation ---
    df['sum_vm_plus'] = df['vm_plus'].rolling(period).sum()
    df['sum_vm_minus'] = df['vm_minus'].rolling(period).sum()
    df['sum_tr'] = df['tr'].rolling(period).sum()
    
    # --- Final VI Calculation ---
    df['VI_Plus'] = df['sum_vm_plus'] / df['sum_tr']
    df['VI_Minus'] = df['sum_vm_minus'] / df['sum_tr']
    
    return df

def main():
    df = get_natural_gas_data()
    if df is None or df.empty: return

    # Calculate components
    df_analysis = calculate_vortex_components(df, period=34)
    
    # Get last 5 rows for context
    tail = df_analysis.tail(5)
    
    print("\n" + "="*80)
    print("📊 NATURAL GAS VORTEX (34) COMPONENT ANALYSIS")
    print("="*80)
    print("This shows the raw numbers used to calculate VI+ and VI-. Compare them to your broker's data.")
    print("-"*80)
    
    for timestamp, row in tail.iterrows():
        print(f"Time: {timestamp.strftime('%H:%M')} | Close: {row['close']:.2f}")
        print(f"  VI+: {row['VI_Plus']:.4f}  <--  SumVM+: {row['sum_vm_plus']:.2f} / SumTR: {row['sum_tr']:.2f}")
        print(f"      Raw Components: Current High: {row['high']:.2f}, Prev Low: {row['prev_low']:.2f} -> VM+: {row['vm_plus']:.2f}")
        print(f"  VI-: {row['VI_Minus']:.4f}  <--  SumVM-: {row['sum_vm_minus']:.2f} / SumTR: {row['sum_tr']:.2f}")
        print(f"      Raw Components: Current Low:  {row['low']:.2f}, Prev High: {row['prev_high']:.2f} -> VM-: {row['vm_minus']:.2f}")
        print("-"*80)
        
    print("\n👉 COMMANDER, please check the 'Raw Components' for a specific candle against your chart's data window.")
    print("   If 'Current High' or 'Prev Low' is different, the data feed is the cause.")

if __name__ == "__main__":
    main()
