"""
UPSTOX HYBRID DATA FETCHER - Complete Fixed Version
King Claude Edition

Features:
- Fetches EXPIRED option data (Sept 25 - Oct 20) using expired-instruments API
- Fetches CURRENT option data (Oct 21, 23, 24) using Intraday V3 API
- Supports 5-minute intervals for both
- Handles errors gracefully
"""

import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import config

# Base URL for Upstox API
BASE_URL = "https://api.upstox.com/v2/"

# ==================== AUTHENTICATION ====================

def load_access_token():
    """Load Upstox access token from session file"""
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "upstox_session.json")
    try:
        with open(file_path, "r") as f:
            session = json.load(f)
            access_token = session.get("access_token")
            if not access_token:
                raise ValueError("No access_token found in upstox_session.json")
            return access_token
    except Exception as e:
        print(f"[ERROR] Failed to load access token: {e}")
        return None

# ==================== EXPIRED INSTRUMENTS API ====================

def get_available_expiries_expired(access_token):
    """Fetch all available EXPIRED expiry dates for NIFTY"""
    index_key = "NSE_INDEX|Nifty 50"
    url = f"{BASE_URL}expired-instruments/expiries?instrument_key={index_key}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"[ERROR] Failed to fetch expired expiries. Status: {resp.status_code}")
        return []
    
    expiries = resp.json().get("data", [])
    return sorted(expiries)

def get_option_contracts_expired(access_token, expiry_date):
    """Fetch option contracts for EXPIRED expiry"""
    index_key = "NSE_INDEX|Nifty 50"
    expiry_str = expiry_date.strftime('%Y-%m-%d')
    url = f"{BASE_URL}expired-instruments/option/contract?instrument_key={index_key}&expiry_date={expiry_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return []
    
    contracts = resp.json().get("data", [])
    return contracts

def get_historical_candles_expired(access_token, expired_instrument_key, target_date):
    """Fetch 5-minute candles for EXPIRED option"""
    date_str = target_date.strftime('%Y-%m-%d')
    url = f"{BASE_URL}expired-instruments/historical-candle/{expired_instrument_key}/5minute/{date_str}/{date_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return pd.DataFrame()
    
    candles = resp.json().get("data", {}).get("candles", [])
    if not candles:
        return pd.DataFrame()
    
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
    df['datetime'] = pd.to_datetime(df['timestamp'])
    df['date'] = target_date
    return df

# ==================== CURRENT INSTRUMENTS API (V3) ====================

def get_available_expiries_current(access_token):
    """
    Get potential current expiries by generating future Tuesdays
    NIFTY now expires on Tuesdays (SEBI change)
    """
    current_expiries = []
    today = datetime.now().date()
    
    # Generate next 8 Tuesdays (covers ~2 months)
    check_date = today
    for _ in range(60):  # Check next 60 days
        if check_date.weekday() == 1:  # Tuesday = 1
            current_expiries.append(check_date.strftime('%Y-%m-%d'))
        check_date += timedelta(days=1)
    
    return current_expiries

def get_option_contracts_current(access_token, expiry_date):
    """Fetch option contracts for CURRENT expiry using option/contract API"""
    index_key = "NSE_INDEX|Nifty 50"
    expiry_str = expiry_date.strftime('%Y-%m-%d')
    
    # URL encode the instrument key
    import urllib.parse
    encoded_key = urllib.parse.quote(index_key, safe='')
    
    url = f"{BASE_URL}option/contract?instrument_key={encoded_key}&expiry_date={expiry_str}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return []
        
        contracts = resp.json().get("data", [])
        return contracts
        
    except Exception as e:
        print(f"[ERROR] Exception in get_option_contracts_current: {e}")
        return []

def get_historical_candles_current_v3(access_token, instrument_key, target_date):
    """
    Fetch 5-minute candles for CURRENT option using HISTORICAL V3 API
    V3 format: /historical-candle/{instrument_key}/{interval}/{unit}/{from_date}/{to_date}
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    date_str = target_date.strftime('%Y-%m-%d')
    
    print(f"[HISTORICAL V3] Fetching 5-minute candles for {target_date}...")
    
    # HISTORICAL V3 endpoint: /{instrument_key}/{interval}/{unit}/{from_date}/{to_date}
    # For 5-minute: /{instrument_key}/5/minutes/2025-10-21/2025-10-21
    url = f"{BASE_URL}historical-candle/{instrument_key}/5/minutes/{date_str}/{date_str}"
    
    print(f"[DEBUG] URL: {url}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            print(f"[HISTORICAL V3] Failed with status {resp.status_code}")
            if resp.status_code == 400:
                error_data = resp.json()
                print(f"[ERROR] {error_data}")
            return pd.DataFrame()
        
        data = resp.json().get("data", {})
        candles = data.get("candles", [])
        
        if not candles:
            print(f"[HISTORICAL V3] No candles returned")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df['date'] = target_date
        
        print(f"[HISTORICAL V3] ✅ SUCCESS! Got {len(df)} candles for {target_date}")
        
        return df
        
    except Exception as e:
        print(f"[HISTORICAL V3] Exception: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
# ==================== HELPER FUNCTIONS ====================

def calculate_atm_strike(spot_price):
    """Round spot price to nearest 50"""
    return int(round(spot_price / 50) * 50)

def get_nearest_expiry(target_date, available_expired, available_current):
    """
    Finds the absolute nearest expiry date on or after the target_date.
    It no longer determines the expiry status.
    """
    all_expiry_dates = set()
    for expiry_str in available_expired:
        all_expiry_dates.add(datetime.strptime(expiry_str, '%Y-%m-%d').date())
    for expiry_str in available_current:
        all_expiry_dates.add(datetime.strptime(expiry_str, '%Y-%m-%d').date())

    valid_expiries = [exp_date for exp_date in all_expiry_dates if exp_date >= target_date]

    if not valid_expiries:
        return None

    return min(valid_expiries, key=lambda x: x - target_date)

def find_atm_instrument_keys(contracts, atm_strike, is_expired):
    """Find instrument keys for ATM CE and ATM PE"""
    ce_key = None
    pe_key = None
    
    for contract in contracts:
        if contract.get("strike_price") == atm_strike:
            # Get the right key based on whether it's expired or current
            if is_expired:
                instrument_key = contract.get("expired_instrument_key") or contract.get("instrument_key")
            else:
                instrument_key = contract.get("instrument_key")
            
            if contract.get("instrument_type") == "CE":
                ce_key = instrument_key
            elif contract.get("instrument_type") == "PE":
                pe_key = instrument_key
    
    return ce_key, pe_key

def find_and_validate_atm_strike(spot_price, contracts, access_token, target_date, is_expired):
    """
    Find the ATM strike, validate its premium, and search for a valid one if needed.
    Returns (atm_strike, ce_key, pe_key) or (None, None, None)
    """
    initial_atm_strike = calculate_atm_strike(spot_price)
    
    # Search strikes around the initial ATM
    for i in range(10):  # Limit search to 10 strikes up/down
        for sign in [1, -1]:
            strike_offset = i * 50 * sign
            current_strike = initial_atm_strike + strike_offset
            
            print(f"[ATM-SEARCH] Trying strike: {current_strike}")
            
            ce_key, pe_key = find_atm_instrument_keys(contracts, current_strike, is_expired)
            
            if not ce_key or not pe_key:
                continue

            # Validate premium
            if is_expired:
                ce_df = get_historical_candles_expired(access_token, ce_key, target_date)
                pe_df = get_historical_candles_expired(access_token, pe_key, target_date)
            else:
                ce_df = get_historical_candles_current_v3(access_token, ce_key, target_date)
                pe_df = get_historical_candles_current_v3(access_token, pe_key, target_date)

            if ce_df.empty or pe_df.empty:
                continue

            ce_premium = ce_df.iloc[0]['open']
            pe_premium = pe_df.iloc[0]['open']
            
            print(f"[ATM-VALIDATE] Strike {current_strike} -> CE: {ce_premium}, PE: {pe_premium}")

            if 50 <= ce_premium <= 180 or 50 <= pe_premium <= 180:
                print(f"[ATM-SUCCESS] Found valid strike: {current_strike}")
                return current_strike, ce_key, pe_key
    
    print(f"[ATM-FAIL] No valid strike found near {initial_atm_strike}")
    return None, None, None

# ==================== MAIN LOGIC ====================

def main():
    print("="*70)
    print("🔥 HYBRID UPSTOX DATA FETCHER - EXPIRED + CURRENT (V3)")
    print("="*70)
    
    # Load access token
    access_token = load_access_token()
    if not access_token:
        print("[FATAL] No access token. Exiting.")
        return
    
    # Load NIFTY index data
    nifty_file = config.NIFTY_DATA_FILE
    print(f"\n[INFO] Loading NIFTY data from: {nifty_file}")
    
    try:
        nifty_df = pd.read_csv(nifty_file)
        nifty_df['datetime'] = pd.to_datetime(nifty_df['datetime'])
        nifty_df['date'] = nifty_df['datetime'].dt.date
    except Exception as e:
        print(f"[FATAL] Failed to load NIFTY data: {e}")
        return
    
    trading_days = sorted(nifty_df['date'].unique())
    print(f"[INFO] Found {len(trading_days)} trading days from {trading_days[0]} to {trading_days[-1]}")
    
    # Fetch available expiries
    print("\n[INFO] Fetching available expiries...")
    available_expired = get_available_expiries_expired(access_token)
    available_current = get_available_expiries_current(access_token)
    
    print(f"[SUCCESS] Expired expiries: {len(available_expired)}")
    print(f"[SUCCESS] Current expiries: {len(available_current)}")
    
    # Storage
    all_option_data = []
    stats = {
        'expired_candles': 0,
        'current_candles': 0,
        'failed_days': 0
    }
    
    # Process each trading day
    # Filter for the last 1 month of trading days
    last_day = trading_days[-1]
    one_month_prior = last_day - timedelta(days=30)
    days_to_process = [day for day in trading_days if day >= one_month_prior]
    
    print(f"\n[INFO] Processing last 1 month: {len(days_to_process)} days from {days_to_process[0]} to {days_to_process[-1]}")

    for day_num, target_date in enumerate(days_to_process, 1):
        print("\n" + "="*70)
        print(f"📅 Processing Day {day_num}/{len(days_to_process)}: {target_date}")
        print("="*70)
        
        # Get 9:15 AM candle for spot price
        day_candles = nifty_df[nifty_df['date'] == target_date]
        candle_915 = day_candles[day_candles['datetime'].dt.time == datetime.strptime('09:15:00', '%H:%M:%S').time()]
        
        if candle_915.empty:
            print(f"[WARNING] No 9:15 AM candle for {target_date}. Using first available.")
            candle_915 = day_candles.head(1)
        
        if candle_915.empty:
            print(f"[ERROR] No data for {target_date}. Skipping.")
            stats['failed_days'] += 1
            continue
        
        spot_price = candle_915.iloc[0]['open']
        
        # Find nearest valid expiry
        expiry_date = get_nearest_expiry(target_date, available_expired, available_current)
        
        if not expiry_date:
            print(f"[ERROR] No suitable expiry found for {target_date}. Skipping.")
            stats['failed_days'] += 1
            continue
        
        # Determine if the found expiry is in the past relative to today's actual date
        # This determines which API to use (expired-instruments vs. standard)
        is_expired_api = expiry_date < datetime.now().date()
        
        # This determines the flag in the final CSV, relative to the processing day
        is_expired_for_csv = expiry_date <= target_date

        expiry_type = "EXPIRED-API" if is_expired_api else "CURRENT-API"
        print(f"[INFO] Spot: {spot_price} | Nearest Expiry: {expiry_date} (Using {expiry_type})")

        # Fetch contracts for the found expiry
        if is_expired_api:
            contracts = get_option_contracts_expired(access_token, expiry_date)
        else:
            contracts = get_option_contracts_current(access_token, expiry_date)
        
        if not contracts:
            print(f"[ERROR] No contracts found for expiry {expiry_date}. Skipping.")
            stats['failed_days'] += 1
            continue
        
        # Find and validate the ATM strike and get keys
        atm_strike, ce_key, pe_key = find_and_validate_atm_strike(spot_price, contracts, access_token, target_date, is_expired_api)

        if not ce_key or not pe_key:
            print(f"[ERROR] Could not find and validate a suitable ATM strike for {target_date}. Skipping.")
            stats['failed_days'] += 1
            continue

        print(f"[SUCCESS] Final Validated ATM: {atm_strike}")
        print(f"[SUCCESS] CE Key: {ce_key}")
        print(f"[SUCCESS] PE Key: {pe_key}")

        # Fetch full day's candle data for the validated instruments
        if is_expired_api:
            ce_df = get_historical_candles_expired(access_token, ce_key, target_date)
            pe_df = get_historical_candles_expired(access_token, pe_key, target_date)
        else:
            ce_df = get_historical_candles_current_v3(access_token, ce_key, target_date)
            pe_df = get_historical_candles_current_v3(access_token, pe_key, target_date)
        
        # Add metadata and store
        if not ce_df.empty:
            ce_df['instrument_type'] = 'CE'
            ce_df['strike_price'] = atm_strike
            ce_df['expiry_date'] = expiry_date
            ce_df['instrument_key'] = ce_key
            ce_df['trading_day'] = target_date
            ce_df['is_expired'] = is_expired_for_csv
            all_option_data.append(ce_df)
            
            candle_count = len(ce_df)
            print(f"[DATA] Stored {candle_count} CE candles.")
            if is_expired_for_csv:
                stats['expired_candles'] += candle_count
            else:
                stats['current_candles'] += candle_count
        else:
            print(f"[ERROR] No CE data fetched for the day.")

        if not pe_df.empty:
            pe_df['instrument_type'] = 'PE'
            pe_df['strike_price'] = atm_strike
            pe_df['expiry_date'] = expiry_date
            pe_df['instrument_key'] = pe_key
            pe_df['trading_day'] = target_date
            pe_df['is_expired'] = is_expired_for_csv
            all_option_data.append(pe_df)
            
            candle_count = len(pe_df)
            print(f"[DATA] Stored {candle_count} PE candles.")
            if is_expired_for_csv:
                stats['expired_candles'] += candle_count
            else:
                stats['current_candles'] += candle_count
        else:
            print(f"[ERROR] No PE data fetched for the day.")
            
        if ce_df.empty and pe_df.empty:
            stats['failed_days'] += 1
    
    # Save results
    print("\n" + "="*70)
    print("💾 SAVING FINAL DATA")
    print("="*70)
    
    if all_option_data:
        final_df = pd.concat(all_option_data, ignore_index=True)
        final_df = final_df.sort_values(['trading_day', 'datetime', 'instrument_type']).reset_index(drop=True)
        
        output_file = 'atm_daily_options_HYBRID_V3.csv'
        final_df.to_csv(output_file, index=False)
        
        total_candles = len(final_df)
        total_days = final_df['trading_day'].nunique()
        
        print(f"\n🎉 SUCCESS! Saved {total_candles} candles to {output_file}")
        print(f"\n📊 STATISTICS:")
        print(f"   Trading days: {total_days}/{len(trading_days)}")
        print(f"   Expired data: {stats['expired_candles']} candles")
        print(f"   Current data: {stats['current_candles']} candles")
        print(f"   Failed days: {stats['failed_days']}")
        
        print(f"\n📋 Sample data:")
        display_cols = ['trading_day', 'datetime', 'instrument_type', 'strike_price', 'close', 'is_expired']
        print(final_df[display_cols].head(10).to_string(index=False))
        
        print(f"\n📅 Daily Summary:")
        for day in sorted(final_df['trading_day'].unique()):
            day_data = final_df[final_df['trading_day'] == day]
            ce_count = len(day_data[day_data['instrument_type'] == 'CE'])
            pe_count = len(day_data[day_data['instrument_type'] == 'PE'])
            strike = day_data['strike_price'].iloc[0]
            expired_flag = "EXPIRED" if day_data['is_expired'].iloc[0] else "CURRENT"
            print(f"   {day}: Strike {strike} | CE: {ce_count} | PE: {pe_count} | {expired_flag}")
    else:
        print("\n[ERROR] No data collected!")
        print(f"Failed days: {stats['failed_days']}/{len(trading_days)}")

if __name__ == "__main__":
    main()