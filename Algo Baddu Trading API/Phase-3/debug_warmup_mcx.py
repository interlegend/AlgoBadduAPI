
import logging
import sys
import os
import json
import requests
from datetime import datetime, timedelta
import urllib.parse

# Import existing config and tools
sys.path.append(os.path.join(os.getcwd(), 'Algo Baddu Trading API', 'Phase-3'))
from config_live import UPSTOX_ACCESS_TOKEN
from commodity_selector import CommodityKeySelector

# Setup Logging to Console
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def debug_mcx_warmup(asset_name="CRUDEOIL"):
    print(f"\n🔍 STARTING WARMUP DEBUG FOR: {asset_name}")
    print("="*60)

    # 1. GET ACTIVE CONTRACT KEY
    print(f"STEP 1: Fetching Active Contract Key...")
    selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
    key, lot, expiry = selector.get_current_future(asset_name)
    
    if not key:
        print(f"❌ FAILED to find active contract for {asset_name}")
        return

    print(f"✅ FOUND KEY: {key} | Expiry: {expiry} | Lot: {lot}")

    # 2. DEFINE DATES
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=5) # 5 Days History
    print(f"\nSTEP 2: Date Range -> From: {from_date} To: {to_date}")

    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    encoded_key = urllib.parse.quote(key, safe='')

    # 3. FETCH HISTORICAL (PAST DAYS)
    print(f"\nSTEP 3: Fetching HISTORICAL Data (Past 5 Days)...")
    url_hist = f"https://api.upstox.com/v3/historical-candle/{encoded_key}/minutes/5/{to_date}/{from_date}"
    
    hist_count = 0
    try:
        res = requests.get(url_hist, headers=headers)
        if res.status_code == 200:
            data = res.json().get("data", {})
            candles = data.get("candles", [])
            hist_count = len(candles)
            print(f"✅ SUCCESS: Fetched {hist_count} Historical Candles")
            if hist_count > 0:
                print(f"   First Candle: {candles[0]}")
                print(f"   Last Candle:  {candles[-1]}")
        else:
            print(f"❌ ERROR: API Status {res.status_code} | Response: {res.text}")
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")

    # 4. FETCH INTRADAY (TODAY)
    print(f"\nSTEP 4: Fetching INTRADAY Data (Today)...")
    url_intra = f"https://api.upstox.com/v3/historical-candle/intraday/{encoded_key}/minutes/5"
    
    intra_count = 0
    try:
        res = requests.get(url_intra, headers=headers)
        if res.status_code == 200:
            data = res.json().get("data", {})
            candles = data.get("candles", [])
            intra_count = len(candles)
            print(f"✅ SUCCESS: Fetched {intra_count} Intraday Candles")
            if intra_count > 0:
                print(f"   First Candle: {candles[0]}")
                print(f"   Last Candle:  {candles[-1]}")
        else:
            print(f"❌ ERROR: API Status {res.status_code} | Response: {res.text}")
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")

    # 5. SUMMARY
    total = hist_count + intra_count
    print("\n" + "="*60)
    print(f"📊 SUMMARY FOR {asset_name} ({key})")
    print(f"   Historical: {hist_count}")
    print(f"   Intraday:   {intra_count}")
    print(f"   TOTAL:      {total}")
    
    if total == 0:
        print("⚠️  CRITICAL FAILURE: ZERO DATA FETCHED.")
    elif total < 50:
        print("⚠️  WARNING: Low Data Count (<50). Indicators will be unstable.")
    else:
        print("✅  DATA LOOKS SUFFICIENT for Warmup.")
    print("="*60 + "\n")

if __name__ == "__main__":
    debug_mcx_warmup("CRUDEOIL")
    debug_mcx_warmup("NATURALGAS")
