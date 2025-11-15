from Dhan_Tradehull import Tradehull
import pandas as pd
from config import CLIENT_ID, ACCESS_TOKEN

# Mock instrument file
instrument_data = {
    "SEM_TRADING_SYMBOL": ["NIFTY-28Sep2025-CE", "NIFTY-28Sep2025-PE"],
    "SEM_CUSTOM_SYMBOL": ["NIFTY", "NIFTY"],
    "SEM_EXPIRY_DATE": ["2025-09-28", "2025-09-28"],
    "SEM_STRIKE_PRICE": [19500, 19500],
    "SEM_OPTION_TYPE": ["CE", "PE"],
    "SEM_EXM_EXCH_ID": ["NSE", "NSE"],
}
instrument_df = pd.DataFrame(instrument_data)

# Initialize Tradehull
tradehull = Tradehull(ClientCode=CLIENT_ID, token_id=ACCESS_TOKEN)
tradehull.instrument_file = instrument_df

# Test ATM Strike Selection
try:
    atm_strikes = tradehull.ATM_Strike_Selection("NIFTY", "2025-09-28")
    print("ATM Strikes:", atm_strikes)
except Exception as e:
    print(e)

# Test Intraday Data Fetch
try:
    intraday_data = tradehull.get_intraday_data("NIFTY", "NSE", "5T")
    print("Intraday Data:", intraday_data)
except Exception as e:
    print(e)