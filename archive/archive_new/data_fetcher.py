
"""
Data Fetcher for Trader-Baddu Phase 2

Handles resilient fetching of OHLC data for indices and options.
"""
from __future__ import annotations

from typing import Optional, List, Union, Dict, Set
import pandas as pd
import pytz
import time
from datetime import datetime

from config import CLIENT_ID, ACCESS_TOKEN, ALIAS_MAP
from Dhan_Tradehull import Tradehull
from order_manager import get_atm_option_symbols

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
            raise RuntimeError(f"Authentication preflight failed. Response: {balance}")
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
    if "timestamp" in df.columns and "datetime" not in df.columns:
        df = df.rename(columns={"timestamp": "datetime"})
    
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"])
        if getattr(df['datetime'].dt, "tz", None) is None:
            df["datetime"] = df["datetime"].dt.tz_localize(IST)
        else:
            df["datetime"] = df["datetime"].dt.tz_convert(IST)
        df = df.sort_values("datetime").drop_duplicates("datetime", keep="last")

    # Ensure essential columns are present
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"OHLC DataFrame missing required column: '{col}'")
    return df

# --------------------------------
# Resilient Symbol OHLC Fetchers
# --------------------------------
def _try_symbols(symbols: Set[str], exchange: str, interval: int) -> pd.DataFrame:
    """Tries multiple symbol aliases until one returns non-empty OHLC data."""
    tsl = _ensure_client()
    for sym in symbols:
        try:
            api_exchange = "INDEX" if exchange == "INDEX" else exchange
            raw = tsl.get_intraday_data(tradingsymbol=sym, exchange=api_exchange, timeframe=interval)
            
            if raw is None or len(raw) == 0:
                continue

            df = pd.DataFrame(raw)
            if not df.empty:
                return _normalize_ohlc_df(df)

        except RuntimeError as e:
            # Catch the specific auth error from Dhan_Tradehull and escalate
            if "Authentication failed" in str(e):
                raise e
            print(f"[WARN] Fetch failed for {sym} ({exchange}, TF={interval}): {e}")
        except Exception as e:
            print(f"[WARN] Unexpected error for {sym} ({exchange}, TF={interval}): {e}")
    return pd.DataFrame()

def get_index_ohlc(
    base_symbol: str,
    interval: Union[int, str] = 5,
    lookback_bars: int = 500
) -> Optional[pd.DataFrame]:
    """
    Fetches OHLC data for a given index (e.g., 'NIFTY', 'BANKNIFTY').
    This function is updated to manually resolve the security ID and call the
    base API directly, bypassing the flawed `get_intraday_data` in the SDK
    which causes a KeyError for the 'INDEX' exchange type.
    """
    tsl = _ensure_client()
    tf = _coerce_timeframe(interval)
    print(f"[FETCH] {base_symbol.upper()} OHLC for interval={tf}m via direct API call.")

    try:
        # 1. Resolve symbol and find its security ID from the instrument master
        canonical_name = next((k for k, v in ALIAS_MAP.items() if base_symbol.upper() in v["aliases"]), None)
        if not canonical_name:
            raise ValueError(f"'{base_symbol}' is not a configured index.")

        instrument_df = tsl.instrument_df
        # For indices, the trading symbol in the master file is the canonical name (e.g., 'NIFTY 50')
        # and the instrument type is 'INDEX'.
        security_check = instrument_df[
            (instrument_df['SEM_TRADING_SYMBOL'].str.upper() == ALIAS_MAP[canonical_name]["master_name"].upper()) &
            (instrument_df['SEM_INSTRUMENT_NAME'].str.upper() == 'INDEX')
        ]

        if security_check.empty:
            raise RuntimeError(f"Manual lookup failed for index '{base_symbol}'. Could not find it in the instrument master.")

        security_id = security_check.iloc[0]['SEM_SMST_SECURITY_ID']
        
        # 2. Direct API call using the resolved security ID
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = start_date
        
        # The exchange_segment for indices is INDEX
        exchange_segment = tsl.Dhan.INDEX
        
        # The underlying API fetches 1-minute data, which we then resample.
        raw_ohlc = tsl.Dhan.intraday_minute_data(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            instrument_type='Index', # Instrument type for indices is 'Index'
            from_date=start_date,
            to_date=end_date,
            interval=1
        )

        if raw_ohlc.get('status') != 'success' or not raw_ohlc.get('data'):
            raise RuntimeError(f"Received empty or failed OHLC response from base API for {base_symbol}")

        df = pd.DataFrame(raw_ohlc['data'])
        df['timestamp'] = df['timestamp'].apply(lambda x: tsl.convert_to_date_time(x))

        # 3. Resample to the desired timeframe if needed
        if tf > 1:
            # Define resampling rules for OHLCV data
            resample_rules = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            # Set timestamp as index for resampling
            df.set_index('timestamp', inplace=True)
            # Resample the dataframe
            df = df.resample(f'{tf}T').apply(resample_rules).dropna()
            df.reset_index(inplace=True)

        # 4. Normalize and return
        df = _normalize_ohlc_df(df)

        if df is None or df.empty:
            print(f"[ERROR] Could not retrieve {base_symbol.upper()} candles after processing.")
            return None

        if len(df) > lookback_bars:
            df = df.iloc[-lookback_bars:].copy()

        if len(df) < 50:
            print(f"[WARN] Insufficient history for {base_symbol.upper()} (<50 bars). Returning what was found.")

        return df

    except Exception as e:
        print(f"[ERROR] Direct fetch for index {base_symbol} failed: {e}")
        # As a fallback, we can try the old method, though it might fail
        print("[WARN] Falling back to legacy _try_symbols method...")
        canonical_name = next((k for k, v in ALIAS_MAP.items() if base_symbol.upper() in v["aliases"]), canonical_name)
        if canonical_name:
            aliases = ALIAS_MAP[canonical_name]["aliases"]
            return _try_symbols(aliases, exchange="INDEX", interval=tf)
        return None

def get_nifty_ohlc(interval: Union[int, str] = 5, lookback_bars: int = 500) -> Optional[pd.DataFrame]:
    """Convenience wrapper to fetch NIFTY index OHLC."""
    return get_index_ohlc("NIFTY", interval, lookback_bars)


def get_nifty_spot_price() -> float:
    """
    Fetches the NIFTY spot price using get_quote_data.
    """
    tsl = _ensure_client()
    try:
        quote = tsl.get_quote_data(names=['NIFTY'])
        if quote and 'NIFTY' in quote:
            return quote['NIFTY']['last_price']
        else:
            raise RuntimeError("Failed to get quote for NIFTY")
    except Exception as e:
        print(f"[FATAL] Could not get NIFTY spot price: {e}")
        raise

def get_option_ohlc(tradingsymbol: str, interval: Union[int, str] = 5, exchange: str = "NFO") -> pd.DataFrame:
    """
    Fetches option OHLC for a given SEM_TRADING_SYMBOL.
    This function contains a workaround to bypass the flawed get_intraday_data in the SDK.
    It performs the instrument lookup manually and calls the base API method directly.
    """
    tsl = _ensure_client()
    tf = _coerce_timeframe(interval)
    
    try:
        instrument_df = tsl.instrument_df
        
        # Manual Lookup: Case-insensitive, hardcoded to look for 'NSE' in the file as that's where NFO instruments are.
        security_check = instrument_df[
            (instrument_df['SEM_TRADING_SYMBOL'].str.upper() == tradingsymbol.upper()) &
            (instrument_df['SEM_EXM_EXCH_ID'] == 'NSE')
        ]

        if security_check.empty:
            raise RuntimeError(f"Manual lookup failed for symbol '{tradingsymbol}'")

        security_id = security_check.iloc[-1]['SEM_SMST_SECURITY_ID']
        instrument_type = security_check.iloc[-1]['SEM_INSTRUMENT_NAME']
        
        # Direct API call, bypassing the broken SDK wrapper function
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = start_date
        
        # The exchange_segment for options is FNO
        exchange_segment = tsl.Dhan.FNO 
        
        # The underlying API fetches 1-minute data, which we then resample.
        raw_ohlc = tsl.Dhan.intraday_minute_data(
            security_id=str(security_id),
            exchange_segment=exchange_segment,
            instrument_type=instrument_type,
            from_date=start_date,
            to_date=end_date,
            interval=1
        )

        if raw_ohlc.get('status') != 'success' or not raw_ohlc.get('data'):
            raise RuntimeError(f"Received empty or failed OHLC response from base API for {tradingsymbol}")

        df = pd.DataFrame(raw_ohlc['data'])
        df['timestamp'] = df['timestamp'].apply(lambda x: tsl.convert_to_date_time(x))

        # Resample to the desired timeframe
        if tf > 1:
            available_frames = {5: '5T', 15: '15T', 60: '60T'} # Simplified for this use case
            df = tsl.resample_timeframe(df, available_frames.get(tf, '5T'))

        return _normalize_ohlc_df(df)

    except Exception as e:
        raise RuntimeError(f"OHLC fetch failed for {tradingsymbol} ({exchange}, TF={tf}): {e}")

# --- Main Execution / Smoke Test ---
if __name__ == "__main__":
    print("[INFO] Testing data_fetcher.py functionality...")
    try:
        set_tsl()
        
        # 1. Fetch NIFTY OHLC
        nifty_data = get_nifty_ohlc(interval=5)
        if nifty_data is not None and not nifty_data.empty:
            print("\n[SUCCESS] Fetched NIFTY OHLC data:")
            print(nifty_data.tail(3))
            spot = nifty_data['close'].iloc[-1]

            # 2. Resolve ATM symbols
            atm_symbols = get_atm_option_symbols(base_symbol="NIFTY", spot=spot)
            ce_sym = atm_symbols["CE_symbol"]
            
            # 3. Fetch Option OHLC
            ce_data = get_option_ohlc(ce_sym, interval=5)
            if ce_data is not None and not ce_data.empty:
                print(f"\n[SUCCESS] Fetched OHLC for ATM CE ({ce_sym}):")
                print(ce_data.tail(3))
            else:
                print(f"[ERROR] Failed to fetch OHLC for {ce_sym}")
        else:
            print("[ERROR] Failed to fetch NIFTY OHLC data.")

    except Exception as e:
        print(f"\n[SMOKE TEST EXCEPTION] {e}")
        import traceback
        traceback.print_exc()
