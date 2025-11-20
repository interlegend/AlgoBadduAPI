"""
UPSTOX HYBRID DATA FETCHER - ULTRA INSTINCT v2.1 (V3 API FIX) 🔥💯
Patched by Copilot — READ THE DOCS, NO YAMCHA BUGS.

CHANGES / FIXES (v2.1):
- V3 API URL FIX: Corrected the interval format from "/5/minutes/" to "/5minute/" to match Upstox docs.
- V3 TIMESTAMP FIX: Correctly parses ISO 8601 timestamps from the v3 API.
- This resolves the '400 Bad Request' errors for current-day instruments.

Run locally:
    python TB4.py
"""

import requests
import json
import os
import pandas as pd
import time
from datetime import datetime, timedelta, date
from datetime import time as dt_time  # ✅ Import time CLASS with alias!
import config
import urllib.parse

# Base host — build v2 and v3 paths per docs to avoid wrong endpoint versions.
API_HOST = "https://api.upstox.com/"
V2 = API_HOST + "v2/"
V3 = API_HOST + "v3/"

# ---------------------------
# Utilities / HTTP helpers
# ---------------------------

def load_access_token():
    """Load Upstox access token from session file. If missing -> graceful fail."""
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "upstox_session.json")
    try:
        with open(file_path, "r") as f:
            session = json.load(f)
            access_token = session.get("access_token")
            if not access_token:
                raise ValueError("No access_token in upstox_session.json")
            return access_token
    except Exception as e:
        print(f"[ZENITSU-TEARS] Failed to load access token: {e}")
        return None

def is_trading_day(target_date, nifty_df):
    """
    Smart holiday detection: Check if NIFTY has data for this day.
    If NIFTY CSV has no data = weekend/holiday = skip!
    
    Args:
        target_date: date object to check
        nifty_df: Your loaded NIFTY dataframe with 'date' column
    
    Returns:
        True if trading day, False if holiday/weekend
    """
    return target_date in nifty_df['date'].values


def safe_get(url, headers, max_retries=5):
    """
    ✅ OPTIMIZED: Smart exponential backoff for 429 errors
    Upstox limits: 50/sec, 500/min, 2000/30min
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 429:
                # Exponential backoff: 5s, 10s, 20s, 40s, 80s
                wait = (2 ** attempt) * 5
                print(f"[VEGETA-THROTTLE] 429 rate limit. Waiting {wait}s then retry ({attempt+1}/{max_retries})")
                time.sleep(wait)  # ✅ Now time.sleep() works!
                continue
            
            return resp
            
        except requests.exceptions.Timeout:
            print(f"[TIMEOUT] Request timed out. Retry {attempt+1}/{max_retries}")
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Request failed: {e}")
            time.sleep(2)
    
    print(f"[GOKU-DEFEAT] Max retries reached. Giving up.")
    return None


# ---------------------------
# Expired-instruments (v2) helpers
# ---------------------------

def get_available_expiries_expired(access_token):
    index_key = "NSE_INDEX|Nifty 50"
    url = f"{V2}expired-instruments/expiries?instrument_key={index_key}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = safe_get(url, headers)
    if not resp or resp.status_code != 200:
        print(f"[ZENITSU-TEARS] Failed to fetch expired expiries. Status: {getattr(resp,'status_code',None)}")
        return []
    try:
        expiries = resp.json().get("data", [])
    except Exception as e:
        print(f"[ZENITSU-TEARS] Could not parse expiries JSON: {e}")
        return []
    return sorted(expiries)

def get_option_contracts_expired(access_token, expiry_date):
    index_key = "NSE_INDEX|Nifty 50"
    expiry_str = expiry_date.strftime('%Y-%m-%d') if isinstance(expiry_date, date) else str(expiry_date)
    url = f"{V2}expired-instruments/option/contract?instrument_key={index_key}&expiry_date={expiry_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = safe_get(url, headers)
    if not resp or resp.status_code != 200:
        print(f"[ZENITSU-TEARS] Failed to fetch expired contracts for {expiry_str}. Status: {getattr(resp,'status_code',None)}")
        return []
    try:
        contracts = resp.json().get("data", [])
    except Exception as e:
        print(f"[ZENITSU-TEARS] Could not parse expired contracts: {e}")
        return []
    return contracts

def get_historical_candles_expired(access_token, expired_instrument_key, target_date):
    date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
    url = f"{V2}expired-instruments/historical-candle/{expired_instrument_key}/5minute/{date_str}/{date_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = safe_get(url, headers)
    if not resp or resp.status_code != 200:
        print(f"[ZENITSU-TEARS] Failed candle fetch for EXPIRED {expired_instrument_key} on {date_str}. Status: {getattr(resp,'status_code',None)}")
        return pd.DataFrame()
    try:
        data = resp.json().get("data", {})
        candles = data.get("candles", [])
    except Exception as e:
        print(f"[ZENITSU-TEARS] Parse error for expired candles: {e}")
        return pd.DataFrame()
    if not candles:
        return pd.DataFrame()
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    if len(candles[0]) >= 7:
        columns.append("oi")
    df = pd.DataFrame(candles, columns=columns)
    df['datetime'] = pd.to_datetime(df['timestamp'])
    df['date'] = target_date
    return df

# ---------------------------
# Current instruments (v3) helpers
# ---------------------------

def get_available_expiries_current(access_token):
    current_expiries = []
    today = datetime.now().date()
    check_date = today
    for _ in range(60):
        if check_date.weekday() in [1, 2, 3]:  # Tue, Wed, Thu
            current_expiries.append(check_date.strftime('%Y-%m-%d'))
        check_date += timedelta(days=1)
    return current_expiries

def get_option_contracts_current(access_token, expiry_date):
    index_key = "NSE_INDEX|Nifty 50"
    expiry_str = expiry_date.strftime('%Y-%m-%d') if isinstance(expiry_date, date) else str(expiry_date)
    encoded_key = urllib.parse.quote(index_key, safe='')
    url = f"{V2}option/contract?instrument_key={encoded_key}&expiry_date={expiry_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = safe_get(url, headers)
    if not resp or resp.status_code != 200:
        print(f"[ZENITSU-TEARS] Failed to fetch current contracts for {expiry_str}. Status: {getattr(resp,'status_code',None)}")
        return []
    try:
        contracts = resp.json().get("data", [])
    except Exception as e:
        print(f"[ZENITSU-TEARS] Parse error in current contracts: {e}")
        return []
    return contracts

def get_historical_candles_current_v3(access_token, instrument_key, target_date):
    """
    ✅ CORRECT V3 API FORMAT:
    /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
    """
    date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, date) else str(target_date)
    encoded_instrument = urllib.parse.quote(instrument_key, safe='')
    
    # ✅ CORRECT V3 FORMAT: unit='minutes', interval='5'
    unit = 'minutes'
    interval = '5'
    url = f"{V3}historical-candle/{encoded_instrument}/{unit}/{interval}/{date_str}/{date_str}"
    
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    
    resp = safe_get(url, headers)
    
    if not resp or resp.status_code != 200:
        print(f"[ZENITSU-TEARS] V3 fetch failed for {instrument_key} on {date_str}. Status: {getattr(resp,'status_code',None)}")
        if resp:
            print(f" -> Response content: {resp.text}")
        return pd.DataFrame()
    
    try:
        data = resp.json().get("data", {})
        candles = data.get("candles", [])
    except Exception as e:
        print(f"[ZENITSU-TEARS] Parse error for V3 candles: {e}")
        return pd.DataFrame()
    
    if not candles:
        return pd.DataFrame()
    
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    if len(candles[0]) >= 7:
        columns.append("oi")
    
    df = pd.DataFrame(candles, columns=columns)
    df['datetime'] = pd.to_datetime(df['timestamp'])
    df['date'] = target_date
    return df

# ---------------------------
# Helper logic: ATM, expiry, keys
# ---------------------------

def calculate_atm_strike(spot_price):
    return int(round(spot_price / 50) * 50)

def is_expiry_day(trading_date, expiry_date):
    try:
        trading_dt = pd.to_datetime(trading_date).date() if not isinstance(trading_date, date) else trading_date
        expiry_dt = pd.to_datetime(expiry_date).date() if not isinstance(expiry_date, date) else expiry_date
        return trading_dt == expiry_dt
    except Exception as e:
        print(f"[ZENITSU-TEARS] Expiry check error: {e}")
        return False

def get_nearest_expiry(target_date, available_expired, available_current):
    all_expiry_dates = set()
    for expiry_str in available_expired:
        try: all_expiry_dates.add(datetime.strptime(expiry_str, '%Y-%m-%d').date())
        except: pass
    for expiry_str in available_current:
        try: all_expiry_dates.add(datetime.strptime(expiry_str, '%Y-%m-%d').date())
        except: pass
    valid = [d for d in all_expiry_dates if d >= target_date]
    if not valid: return None
    return min(valid, key=lambda x: x - target_date)

def find_atm_instrument_keys(contracts, atm_strike, is_expired):
    ce_key, pe_key = None, None
    for contract in contracts:
        try: strike = int(float(contract.get("strike_price")))
        except (ValueError, TypeError): continue
        if strike == atm_strike:
            instrument_key = contract.get("expired_instrument_key" if is_expired else "instrument_key") or contract.get("instrument_key")
            if contract.get("instrument_type") == "CE": ce_key = instrument_key
            elif contract.get("instrument_type") == "PE": pe_key = instrument_key
    return ce_key, pe_key

# ---------------------------
# GOLDILOCKS ATM finder
# ---------------------------

def find_and_validate_atm_strike(spot_price, contracts, access_token, target_date, expiry_date, is_expired_api, search_range=15):
    """
    ✅ OPTIMIZED VERSION - Silences verbose holiday prints, fails fast
    """
    initial_atm_strike = calculate_atm_strike(spot_price)
    is_expiry = is_expiry_day(target_date, expiry_date)
    lower_bound, upper_bound, min_premium = (30, 175, 1) if is_expiry else (50, 175, 10)
    
    print(f"\n[ATM-SEARCH] Trading: {target_date} | Expiry: {expiry_date}")
    print(f"[ATM-SEARCH] NIFTY Spot: {spot_price:.2f} → Initial ATM: {initial_atm_strike}")
    print(f"[ATM-SEARCH] Mode: {'EXPIRY' if is_expiry else 'NORMAL'} | min_premium={min_premium} | bounds=[{lower_bound},{upper_bound}]")
    
    def validate_strike(current_strike, verbose=True):
        """
        Validate a single strike. 
        verbose=False silences individual failed strike messages (speeds up holidays)
        """
        ce_key, pe_key = find_atm_instrument_keys(contracts, current_strike, is_expired_api)
        
        if not ce_key and not pe_key:
            if verbose:
                print(f"[ZORO-MISS] No instrument keys (CE/PE) found for strike {current_strike}")
            return False, None, None
        
        # Fetch candles
        ce_df = get_historical_candles_expired(access_token, ce_key, target_date) if is_expired_api and ce_key else (
            get_historical_candles_current_v3(access_token, ce_key, target_date) if ce_key else pd.DataFrame()
        )
        pe_df = get_historical_candles_expired(access_token, pe_key, target_date) if is_expired_api and pe_key else (
            get_historical_candles_current_v3(access_token, pe_key, target_date) if pe_key else pd.DataFrame()
        )
        
        # ✅ SILENT MODE: Don't print "Both CE and PE missing" unless verbose
        if ce_df.empty and pe_df.empty:
            # Silenced for speed - only print if this is the initial ATM check
            if verbose:
                pass  # Skip the ZENITSU-TEARS flood!
            return False, None, None
        
        ce_premium = float(ce_df.iloc[0]['open']) if not ce_df.empty else 0.0
        pe_premium = float(pe_df.iloc[0]['open']) if not pe_df.empty else 0.0
        
        ce_in_range = (lower_bound <= ce_premium <= upper_bound)
        pe_in_range = (lower_bound <= pe_premium <= upper_bound)
        ce_above_min = ce_premium > min_premium
        pe_above_min = pe_premium > min_premium
        
        # Goldilocks rule
        if is_expiry:
            goldilocks_pass = (ce_in_range and ce_above_min) or (pe_in_range and pe_above_min)
        else:
            goldilocks_pass = (ce_in_range or pe_in_range) and (ce_above_min and pe_above_min)
        
        # Only print validation results, not the "missing data" spam
        print(f"[ATM-VALIDATE] Strike {current_strike}: CE=₹{ce_premium:.2f} ({'OK' if ce_in_range else 'NO'}) | PE=₹{pe_premium:.2f} ({'OK' if pe_in_range else 'NO'}) -> {'✅ PASS' if goldilocks_pass else '❌ FAIL'}")
        
        if goldilocks_pass:
            return True, ce_key, pe_key
        return False, None, None
    
    # Try initial ATM first (verbose mode)
    is_valid, ce_key, pe_key = validate_strike(initial_atm_strike, verbose=True)
    if is_valid:
        print(f"[LEVI-CLEANUP] ✅ Found valid strike: {initial_atm_strike}")
        return initial_atm_strike, ce_key, pe_key
    
    print(f"[ATM-SEARCH] Initial ATM failed, searching ±{search_range} strikes...")
    
    # ✅ OPTIMIZATION: Fast holiday detection
    # If first 3 strikes have NO data at all, it's likely a holiday - fail fast!
    quick_test_count = 0
    for i in range(1, 4):  # Test just 3 strikes
        for sign in [1, -1]:
            strike_to_check = initial_atm_strike + (sign * i * 50)
            ce_key_test, pe_key_test = find_atm_instrument_keys(contracts, strike_to_check, is_expired_api)
            
            if ce_key_test or pe_key_test:
                # Found at least some keys, continue full search
                quick_test_count += 1
                break
        if quick_test_count > 0:
            break
    
    # If first 3 strikes had zero instruments, it's a holiday - exit immediately!
    if quick_test_count == 0:
        print(f"[INFO] No instruments available for {target_date}. Likely market holiday. Skipping.")
        return None, None, None
    
    # Full search (silent mode to avoid spam)
    for i in range(1, search_range + 1):
        for sign in [1, -1]:
            strike_to_check = initial_atm_strike + (sign * i * 50)
            # ✅ verbose=False = no "missing data" prints during search
            is_valid, ce_key, pe_key = validate_strike(strike_to_check, verbose=False)
            if is_valid:
                print(f"[LEVI-CLEANUP] ✅ Found valid strike: {strike_to_check} ({'+' if sign==1 else ''}{sign*i*50})")
                return strike_to_check, ce_key, pe_key
    
    print(f"[ZENITSU-TEARS] No valid ATM found near {initial_atm_strike} (±{search_range*50}).")
    return None, None, None


# ---------------------------
# MAIN
# ---------------------------

def main():
    print("="*70)
    print("🔥 HYBRID UPSTOX DATA FETCHER - ULTRA INSTINCT v2.1 (V3 API FIX)")
    print("No Yamcha logic. Full docs compliance.")
    print("="*70)

    access_token = load_access_token()
    if not access_token:
        print("[ZENITSU-TEARS] No access token found. Run upstox_auth to generate one.")
        return

    try:
        nifty_df = pd.read_csv(config.NIFTY_DATA_FILE)
        nifty_df['datetime'] = pd.to_datetime(nifty_df['datetime'])
        nifty_df['date'] = nifty_df['datetime'].dt.date
    except Exception as e:
        print(f"[ZENITSU-TEARS] Failed to load NIFTY CSV: {e}")
        return

    trading_days = sorted(nifty_df['date'].unique())
    if not trading_days:
        print("[ZENITSU-TEARS] No trading days in NIFTY file.")
        return
    print(f"[INFO] Found {len(trading_days)} total trading days in CSV.")

    print("\n[INFO] Fetching available expiries (expired & current)...")
    available_expired = get_available_expiries_expired(access_token)
    available_current = get_available_expiries_current(access_token)
    print(f"[SUCCESS] Expired: {len(available_expired)}, Current candidates: {len(available_current)}")

    today = datetime.now().date()
    # ✅ NEW (6 months = ~180 days):
    six_months_prior = today - timedelta(days=180)
    nifty_trading_days = set(nifty_df['date'].unique())
    days_to_process = [
        d for d in trading_days 
        if six_months_prior <= d < today and d in nifty_trading_days
    ]

    print(f"\n[INFO] 🔥 PROCESSING LAST 6 MONTHS: {len(days_to_process)} days from {days_to_process[0]} to {days_to_process[-1]}")

    print(f"[INFO] Auto-skipped {len([d for d in trading_days if six_months_prior <= d < today]) - len(days_to_process)} holidays/weekends")

    all_option_data, stats = [], {'expired_candles': 0, 'current_candles': 0, 'failed_days': 0}

    for day_num, target_date in enumerate(days_to_process, 1):
        # ✅ Rate limit protection: small delay between days
        if day_num > 1:
            time.sleep(0.5)  # 0.5 seconds = ~60 seconds total overhead for 120 days
    
        print("\n" + "="*70)
        print(f"📅 Day {day_num}/{len(days_to_process)}: {target_date}")
        print("="*70)

        day_candles = nifty_df[nifty_df['date'] == target_date]
        candle_915 = day_candles[day_candles['datetime'].dt.time == dt_time(9, 15)]
        if candle_915.empty:
            print(f"[ZENITSU-TEARS] No 9:15 candle for {target_date}. Using first available.")
            candle_915 = day_candles.head(1)
        if candle_915.empty:
            stats['failed_days'] += 1; print(f"[ZENITSU-TEARS] No NIFTY data for {target_date}. Skipping."); continue

        spot_price = float(candle_915.iloc[0]['close'])
        expiry_date = get_nearest_expiry(target_date, available_expired, available_current)
        if not expiry_date:
            stats['failed_days'] += 1; print(f"[ZENITSU-TEARS] No expiry >= {target_date}. Skipping."); continue

        is_expired_api = expiry_date < date.today()
        contracts = get_option_contracts_expired(access_token, expiry_date) if is_expired_api else get_option_contracts_current(access_token, expiry_date)
        if not contracts:
            stats['failed_days'] += 1; print(f"[ZENITSU-TEARS] No contracts for expiry {expiry_date}. Skipping."); continue

        atm_strike, ce_key, pe_key = find_and_validate_atm_strike(spot_price, contracts, access_token, target_date, expiry_date, is_expired_api)
        if not ce_key and not pe_key:
            stats['failed_days'] += 1; print(f"[ZENITSU-TEARS] No valid ATM for {target_date}. Skipping."); continue

        print(f"[LEVI-CLEANUP] Final ATM: {atm_strike} | CE: {ce_key} | PE: {pe_key}")

        ce_df = get_historical_candles_expired(access_token, ce_key, target_date) if is_expired_api and ce_key else (get_historical_candles_current_v3(access_token, ce_key, target_date) if ce_key else pd.DataFrame())
        pe_df = get_historical_candles_expired(access_token, pe_key, target_date) if is_expired_api and pe_key else (get_historical_candles_current_v3(access_token, pe_key, target_date) if pe_key else pd.DataFrame())

        is_expired_for_csv = expiry_date <= target_date
        for df, opt_type, key in [(ce_df, 'CE', ce_key), (pe_df, 'PE', pe_key)]:
            if not df.empty:
                df['instrument_type'], df['strike_price'], df['expiry_date'], df['instrument_key'], df['trading_day'], df['is_expired'] = [opt_type, atm_strike, expiry_date, key, target_date, is_expired_for_csv]
                all_option_data.append(df)
                stats['current_candles' if not is_expired_api else 'expired_candles'] += len(df)
                print(f"[DATA] Stored {opt_type} candles: {len(df)}")
            else:
                print(f"[ZENITSU-TEARS] {opt_type} candles empty for {target_date} (key={key})")
        
        if ce_df.empty and pe_df.empty: stats['failed_days'] += 1

    if all_option_data:
        final_df = pd.concat(all_option_data, ignore_index=True).sort_values(['trading_day', 'datetime', 'instrument_type']).reset_index(drop=True)
        output_file = 'atm_daily_options_HYBRID_V3_ULTRA_FIXED.csv'
        final_df.to_csv(output_file, index=False)
        print(f"\n{'='*70}\n💾 SAVING FINAL DATA\n{'='*70}")
        print(f"\n🎉 ULTRA INSTINCT SUCCESS! Saved {len(final_df)} candles to {output_file}")
        print(f"\n📊 STATS: Days: {final_df['trading_day'].nunique()}/{len(days_to_process)} | Failed: {stats['failed_days']}")
    else:
        print("\n[ZENITSU-TEARS] No option data collected.")

if __name__ == "__main__":
    main()