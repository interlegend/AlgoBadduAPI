"""
Order Manager for Trader-Baddu Phase 2
Handles ATM option symbol resolution from the instrument master file.
"""
import os
import glob
import pandas as pd
from datetime import datetime
import pytz
from typing import Dict, Set

from config import ALIAS_MAP

# --- CONFIGURATION ---
IST = pytz.timezone("Asia/Kolkata")

def _find_canonical_symbol(base_symbol: str) -> str:
    """Find the canonical name for a given alias (e.g., 'NIFTY 50' -> 'NIFTY')."""
    base_symbol_upper = base_symbol.upper()
    for canonical, details in ALIAS_MAP.items():
        if base_symbol_upper in details["aliases"]:
            return canonical
    raise ValueError(f"Symbol '{base_symbol}' is not a recognized alias.")

def _get_symbol_details(canonical_symbol: str) -> Dict:
    """Get the step and aliases for a canonical symbol."""
    return ALIAS_MAP[canonical_symbol]

def _normalize_instruments(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize instrument CSV column names and parse essential types."""
    # Use a case-insensitive mapping to find columns
    cols = {c.lower(): c for c in df.columns}
    
    def pick(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    # Define canonical column names we need
    renames = {
        pick("sem_trading_symbol", "tradingsymbol"): "SEM_TRADING_SYMBOL",
        pick("sem_custom_symbol", "symbol", "underlying"): "UNDERLYING",
        pick("sem_expiry_date", "expiry"): "EXPIRY",
        pick("sem_strike_price", "strike"): "STRIKE_PRICE",
        pick("sem_option_type", "option_type"): "OPTION_TYPE",
        pick("sem_exm_exch_id", "exchange"): "EXCHANGE",
    }
    
    # Filter out None keys before renaming
    df = df.rename(columns={k: v for k, v in renames.items() if k})

    # --- Type Coercion ---
    if "EXPIRY" in df.columns:
        df["EXPIRY"] = pd.to_datetime(df["EXPIRY"], errors="coerce").dt.date
    if "STRIKE_PRICE" in df.columns:
        df["STRIKE_PRICE"] = pd.to_numeric(df["STRIKE_PRICE"], errors="coerce")
    
    # --- String Normalization ---
    for col in ["UNDERLYING", "OPTION_TYPE", "EXCHANGE", "SEM_TRADING_SYMBOL"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            
    return df

def _latest_instrument_csv() -> str:
    """
    Finds the most recent instrument CSV in the project's root 'Dependencies' folder,
    with a fallback to the local 'Dependencies' folder.
    """
    # This script is in a subdirectory (e.g., 'TB DHAN API ALGO').
    # We want to find the 'Dependencies' folder at the project root.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # Assumes one level down from root

    # Primary search path: <project_root>/Dependencies/all_instrument*.csv
    primary_pattern = os.path.join(project_root, 'Dependencies', 'all_instrument*.csv')
    files = sorted(glob.glob(primary_pattern, recursive=False), key=os.path.getmtime)

    if files:
        return files[-1]

    # Fallback search path: <script_dir>/Dependencies/all_instrument*.csv
    fallback_pattern = os.path.join(script_dir, 'Dependencies', 'all_instrument*.csv')
    files = sorted(glob.glob(fallback_pattern, recursive=False), key=os.path.getmtime)
    
    if files:
        print("[WARN] Using fallback instrument file location. Consider moving to root Dependencies folder.")
        return files[-1]

    raise FileNotFoundError(f"No instrument CSV found in primary ({primary_pattern}) or fallback locations.")

def get_atm_option_symbols(
    base_symbol: str,
    spot: float,
    when_dt: datetime = None,
    instrument_csv_path: str = None,
) -> Dict[str, any]:
    """
    Resolves ATM Call/Put option symbols for a given underlying index.

    This is the primary function for Phase 2 symbol resolution. It performs:
    1. Canonical symbol resolution (e.g., 'NIFTY BANK' -> 'BANKNIFTY').
    2. Dynamic strike calculation based on the symbol's step value.
    3. Instrument master loading and normalization.
    4. Filtering to find the correct CE/PE trading symbols for the ATM strike
       and the nearest valid expiry.

    Args:
        base_symbol: The index to find options for (e.g., "NIFTY", "BANKNIFTY").
        spot: The current spot price of the index.
        when_dt: The datetime to resolve for (defaults to now). Used for expiry selection.
        instrument_csv_path: Optional path to the instrument master. If None, finds the latest.

    Returns:
        A dictionary containing:
        - 'CE_symbol': The trading symbol for the ATM call option.
        - 'PE_symbol': The trading symbol for the ATM put option.
        - 'exchange': The exchange of the symbols (e.g., 'NFO').
        - 'expiry': The expiry date of the options.
        - 'strike': The calculated ATM strike price.
    """
    if when_dt is None:
        when_dt = datetime.now(IST)
    when_date = when_dt.astimezone(IST).date()

    # 1. Resolve symbol and get its properties
    canonical_symbol = _find_canonical_symbol(base_symbol)
    symbol_details = _get_symbol_details(canonical_symbol)
    aliases: Set[str] = symbol_details["aliases"]
    step: int = symbol_details["step"]

    # 2. Calculate ATM strike
    atm_strike = round(float(spot) / step) * step

    # 3. Load and normalize instrument master
    if instrument_csv_path is None:
        instrument_csv_path = _latest_instrument_csv()
    
    inst_df = pd.read_csv(instrument_csv_path, low_memory=False)
    inst_df = _normalize_instruments(inst_df)

    # 4. Filter for relevant option contracts
    q = inst_df[
        inst_df["UNDERLYING"].str.startswith(canonical_symbol)
        & inst_df["STRIKE_PRICE"].notna()
        & inst_df["OPTION_TYPE"].isin(["CE", "PE"])
        & (inst_df["EXPIRY"] >= when_date)
    ].copy()

    if q.empty:
        raise ValueError(f"No future options found for '{canonical_symbol}' in the instrument master.")

    # Find the earliest expiry date available
    earliest_expiry = q["EXPIRY"].min()
    q = q[q["EXPIRY"] == earliest_expiry]

    # Find options at the exact ATM strike
    q_atm = q[q["STRIKE_PRICE"] == atm_strike]

    ce_row = q_atm[q_atm["OPTION_TYPE"] == "CE"].head(1)
    pe_row = q_atm[q_atm["OPTION_TYPE"] == "PE"].head(1)

    # Fallback: if no exact match, find nearest strike
    if ce_row.empty or pe_row.empty:
        q['strike_diff'] = (q['STRIKE_PRICE'] - spot).abs()
        nearest_strike = q.sort_values('strike_diff').iloc[0]['STRIKE_PRICE']
        q_nearest = q[q['STRIKE_PRICE'] == nearest_strike]
        
        ce_row = q_nearest[q_nearest["OPTION_TYPE"] == "CE"].head(1)
        pe_row = q_nearest[q_nearest["OPTION_TYPE"] == "PE"].head(1)
        atm_strike = nearest_strike


    if ce_row.empty or pe_row.empty:
        raise ValueError(f"Could not find valid CE/PE pair for '{canonical_symbol}' near strike {atm_strike} for expiry {earliest_expiry}.")

    # 5. Extract results
    ce_symbol = ce_row["SEM_TRADING_SYMBOL"].iloc[0]
    pe_symbol = pe_row["SEM_TRADING_SYMBOL"].iloc[0]
    exchange = ce_row["EXCHANGE"].iloc[0]

    result = {
        "CE_symbol": str(ce_symbol),
        "PE_symbol": str(pe_symbol),
        "exchange": str(exchange),
        "expiry": earliest_expiry,
        "strike": atm_strike,
    }
    
    print(f"[ATM-RESOLVER] spot={float(spot):.2f} base='{base_symbol}' -> ATM Strike={atm_strike} Expiry={result['expiry']} CE={result['CE_symbol']} PE={result['PE_symbol']}")
    return result