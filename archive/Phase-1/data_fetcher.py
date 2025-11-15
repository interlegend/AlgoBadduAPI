
"""
Data Fetcher for Trader-Baddu Phase 2 (Corrected)

Handles resilient fetching of OHLC data for indices and options,
with proper historical data support.
"""
from __future__ import annotations

from typing import Optional, Union
import pandas as pd
import pytz
from datetime import datetime, timedelta

from trader_config import CLIENT_ID, ACCESS_TOKEN, ALIAS_MAP
from Dhan_Tradehull import Tradehull

# --- CONFIGURATION ---
IST = pytz.timezone("Asia/Kolkata")
_TSL: Optional[Tradehull] = None
_VALID_TF = {1, 2, 3, 5, 10, 15, 30, 60}

# ---------------------------
# Client Bootstrap & Preflight
# ---------------------------
def set_tsl(client: Optional[Tradehull] = None) -> None:
    """Initializes the global Tradehull client, with an auth preflight check."""
    global _TSL
    if client is None:
        print(f"[INFO] Initializing Tradehull client...")
        client = Tradehull(ClientCode=CLIENT_ID, token_id=ACCESS_TOKEN)
    _TSL = client

    try:
        balance = _TSL.get_balance()
        if isinstance(balance, (int, float)) and balance >= 0:
            print(f"[SUCCESS] Tradehull client authenticated. Available balance: {balance}")
        else:
            # Allow continuing even if auth fails, to see code errors
            print(f"[WARN] Could not verify authentication. Response: {balance}")
    except Exception as e:
        print(f"[FATAL] Could not init TradeHull client (token/auth): {e}")
        raise

def _ensure_client(auto_init: bool = True) -> Tradehull:
    """Ensures the TradeHull client is initialized, calling set_tsl() if needed."""
    global _TSL
    if _TSL is None:
        if auto_init:
            set_tsl()
        else:
            raise RuntimeError("TradeHull client not initialized. Call set_tsl() first.")
    return _TSL

# ---------------------------
# Utilities
# ---------------------------
def _coerce_timeframe(tf: Union[int, str, None], default: int = 5) -> int:
    """Coerces a timeframe string/int to a valid integer."""
    if tf is None: return default
    try:
        tf = int(str(tf).strip().lower().replace("m", ""))
        if tf not in _VALID_TF:
            raise ValueError(f"Invalid timeframe '{tf}'. Allowed: {_VALID_TF}")
        return tf
    except (ValueError, TypeError) as e:
        raise ValueError(f"Could not parse timeframe '{tf}': {e}")

def _normalize_ohlc_df(df: pd.DataFrame) -> pd.DataFrame:
    """Renames timestamp, normalizes timezone, and sorts an OHLC DataFrame."""
    if df.empty:
        return df
        
    # The historical API returns 'start_Time', intraday returns 'timestamp'
    if 'start_Time' in df.columns:
         df['datetime'] = df['start_Time'].apply(lambda x: _ensure_client().convert_to_date_time(x))
    elif 'timestamp' in df.columns:
        df = df.rename(columns={"timestamp": "datetime"})

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"])
        if getattr(df['datetime'].dt, "tz", None) is None:
            df["datetime"] = df["datetime"].dt.tz_localize(IST)
        else:
            df["datetime"] = df["datetime"].dt.tz_convert(IST)
        df = df.sort_values("datetime").reset_index(drop=True)

    # Ensure essential columns are present
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0
    return df

# --------------------------------
# Core Historical Data Fetcher
# --------------------------------
def _fetch_historical_intraday(
    tradingsymbol: str,
    exchange: str,
    interval: int,
    from_date: str,
    to_date: str
) -> pd.DataFrame:
    """
    Correctly fetches historical intraday data by bypassing the buggy Tradehull wrapper
    and calling the underlying dhanhq library method directly.
    """
    tsl = _ensure_client()
    instrument_df = tsl.instrument_df
    
    # This logic is replicated from Dhan_Tradehull.py to find the security ID and segment
    script_exchange_map = {"NSE": "NSE", "NFO": "FNO", "BSE": "BSE", "BFO": "BFO", "MCX": "MCX", "CUR": "CUR", "INDEX": "INDEX"}
    api_segment = getattr(tsl.Dhan, script_exchange_map.get(exchange))

    instrument_exchange_map = {'NSE':'NSE','BSE':'BSE','NFO':'NSE','BFO':'BSE','MCX':'MCX','CUR':'NSE', 'INDEX': 'NSE'}
    search_exchange = instrument_exchange_map.get(exchange)

    security_check = instrument_df[
        ((instrument_df['SEM_TRADING_SYMBOL'] == tradingsymbol) | (instrument_df['SEM_CUSTOM_SYMBOL'] == tradingsymbol)) &
        (instrument_df['SEM_EXM_EXCH_ID'] == search_exchange)
    ]
    
    if security_check.empty:
        # Try again with aliases for indices
        if exchange == 'INDEX':
            for alias in ALIAS_MAP.get(tradingsymbol, {}).get('aliases', []):
                 security_check = instrument_df[
                    ((instrument_df['SEM_TRADING_SYMBOL'] == alias) | (instrument_df['SEM_CUSTOM_SYMBOL'] == alias)) &
                    (instrument_df['SEM_EXM_EXCH_ID'] == search_exchange)
                ]
                 if not security_check.empty:
                     tradingsymbol = alias
                     break
    
    if security_check.empty:
        raise ValueError(f"Could not find security ID for '{tradingsymbol}' on exchange '{search_exchange}'")

    security_id = str(security_check.iloc[-1]['SEM_SMST_SECURITY_ID'])
    
    instrument_type = security_check.iloc[-1]['SEM_INSTRUMENT_NAME']

    # The dhanhq `intraday_minute_data` requires a 1-minute interval. We will fetch that and resample.
    raw_ohlc = tsl.Dhan.intraday_minute_data(security_id, api_segment, instrument_type, from_date, to_date, 1)

    if raw_ohlc.get('status') != 'success' or not raw_ohlc.get('data'):
        print(f"[WARN] No data returned from API for {tradingsymbol} from {from_date} to {to_date}. Response: {raw_ohlc.get('remarks')}")
        return pd.DataFrame()

    df = pd.DataFrame(raw_ohlc['data'])
    normalized_df = _normalize_ohlc_df(df)

    # Resample to the desired timeframe if it's not 1 minute
    if interval > 1 and not normalized_df.empty:
        resample_period = f'{interval}T'
        normalized_df.set_index('datetime', inplace=True)
        resampled_df = normalized_df.resample(resample_period).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna(how='all').reset_index()
        return resampled_df

    return normalized_df

# --------------------------------
# Public-Facing Fetcher Functions
# --------------------------------
def get_index_ohlc(
    base_symbol: str,
    interval: Union[int, str] = 5, # Interval is ignored for this daily fetch, but kept for signature consistency
    lookback_days: int = 90
) -> Optional[pd.DataFrame]:
    """Fetches historical DAILY OHLC data for a given index."""
    print(f"[FETCH] {base_symbol.upper()} DAILY OHLC for last {lookback_days} days.")
    tsl = _ensure_client()
    
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

    try:
        # Find the canonical name and all its aliases
        canonical_name = next((k for k, v in ALIAS_MAP.items() if base_symbol.upper() in v["aliases"]), base_symbol.upper())
        aliases_to_check = ALIAS_MAP.get(canonical_name, {}).get('aliases', {canonical_name})

        instrument_df = tsl.instrument_df
        security_id = None

        # Loop through aliases to find a valid security ID
        for alias in aliases_to_check:
            security_check = instrument_df[
                ((instrument_df['SEM_TRADING_SYMBOL'] == alias) | (instrument_df['SEM_CUSTOM_SYMBOL'] == alias)) &
                (instrument_df['SEM_EXM_EXCH_ID'] == 'NSE') & # Indices are on NSE
                (instrument_df['SEM_INSTRUMENT_NAME'] == 'INDEX')
            ]
            if not security_check.empty:
                security_id = str(security_check.iloc[-1]['SEM_SMST_SECURITY_ID'])
                break # Found it
        
        if security_id is None:
            raise ValueError(f"Could not find security ID for index '{canonical_name}' using any alias.")

        raw_ohlc = tsl.Dhan.historical_daily_data(
            security_id=security_id,
            exchange_segment=tsl.Dhan.INDEX,
            instrument_type='INDEX',
            from_date=from_date,
            to_date=to_date
        )

        if raw_ohlc.get('status') != 'success' or not raw_ohlc.get('data'):
            print(f"[ERROR] Could not retrieve {base_symbol.upper()} daily candles.")
            return None

        df = pd.DataFrame(raw_ohlc['data'])
        return _normalize_ohlc_df(df)

    except Exception as e:
        print(f"[ERROR] Fetch for daily index {base_symbol} failed: {e}")
        return None

def get_nifty_ohlc(interval: Union[int, str] = 5, lookback_days: int = 35) -> Optional[pd.DataFrame]:
    """Convenience wrapper to fetch NIFTY index OHLC."""
    return get_index_ohlc("NIFTY", interval, lookback_days)

def get_nifty_spot_price() -> float:
    """Fetches the live NIFTY spot price."""
    tsl = _ensure_client()
    try:
        ltp_data = tsl.get_ltp_data('NIFTY')
        if ltp_data and 'NIFTY' in ltp_data:
            return ltp_data['NIFTY']
        raise RuntimeError("LTP data for NIFTY not found in response.")
    except Exception as e:
        print(f"[FATAL] Could not fetch NIFTY spot price: {e}")
        raise

def get_option_ohlc(
    tradingsymbol: str,
    interval: Union[int, str],
    exchange: str = 'NFO',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetches option OHLC. If start/end dates are given, fetches historical data.
    Otherwise, fetches data for the current day.
    """
    tf = _coerce_timeframe(interval)
    
    if start_date is None or end_date is None:
        # Default to current day if no range is specified
        start_date = end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"[FETCH] Option OHLC for {tradingsymbol} (TF={tf}m) from {start_date} to {end_date}")
    
    try:
        return _fetch_historical_intraday(tradingsymbol, exchange, tf, start_date, end_date)
    except Exception as e:
        print(f"OHLC fetch failed for {tradingsymbol} ({exchange}, TF={tf}): {e}")
        # Return empty dataframe on failure to prevent downstream crashes
        return pd.DataFrame()
