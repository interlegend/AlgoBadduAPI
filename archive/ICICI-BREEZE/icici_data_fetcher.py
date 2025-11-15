from breeze_connect import BreezeConnect
import pandas as pd
from icici_config import API_KEY, API_SECRET
import argparse
import json
from datetime import datetime, timedelta
import os
import urllib.parse

SESSION_FILE = "breeze_session.json"

def save_session(breeze):
    session = {
        "session_token": breeze.session_key, # <-- This is our hard-won fix!
        "login_time": datetime.now().isoformat()
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(session, f)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            session = json.load(f)
            login_time = datetime.fromisoformat(session["login_time"])
            if datetime.now() - login_time < timedelta(hours=23):
                return session["session_token"]
    return None

def authenticate_icici(force_setup=False):
    """
    Handles the two-step authentication process for the ICICI Breeze API.
    """
    session_token = load_session()
    if session_token and not force_setup:
        try:
            breeze = BreezeConnect(api_key=API_KEY)
            breeze.generate_session(api_secret=API_SECRET, session_token=session_token)
            print("SUCCESS! ICICI Breeze session restored from file!")
            return breeze
        except Exception as e:
            print(f"Could not restore session: {e}. Re-authenticating...")

    # This is the "Goku-Gemini Fusion" / "Official Doc" strategy. It is correct.
    breeze = BreezeConnect(api_key=API_KEY)

    encoded_api_key = urllib.parse.quote_plus(API_KEY)
    login_url = f"https://api.icicidirect.com/apiuser/login?api_key={encoded_api_key}"
    print(f"Commander, please log in at this URL: {login_url}")

    redirect_url_paste = input("Commander, please paste the FULL redirect URL (from 127.0.0.1): ")

    parsed_url = urllib.parse.urlparse(redirect_url_paste)
    auth_token = urllib.parse.parse_qs(parsed_url.query)['apisession'][0]

    breeze.generate_session(
        api_secret=API_SECRET,
        session_token=auth_token
    )
    print("SUCCESS! ICICI Breeze session is live and ready to fire!")
    save_session(breeze)
    return breeze

# ---------------------------------------------------------
# THE NEW FIX IS HERE!
# ---------------------------------------------------------
def fetch_option_data(breeze_client, from_date, to_date, strike, expiry, right):
    """
    Fetches historical option data using breeze.get_historical_data_v2.
    """
    print(f"Fetching {right} option data for strike {strike} and expiry {expiry} from {from_date} to {to_date}")
    
    # -----------------
    # FIX: Using the exact T05:30:00.000Z (IST) format from the docs!
    # -----------------
    from_date_iso = f'{from_date}T05:30:00.000Z'
    to_date_iso = f'{to_date}T18:00:00.000Z' # 18:00 is fine for end-of-day
    expiry_iso = f'{expiry}T05:30:00.000Z'

    try:
        data = breeze_client.get_historical_data_v2(
            interval='5minute',
            from_date=from_date_iso, # <-- Using new fixed var
            to_date=to_date_iso,
            stock_code='NIFTY',
            exchange_code='NFO',
            product_type='options',
            expiry_date=expiry_iso, # <-- Using new fixed var
            right=right,
            strike_price=str(strike)
        )

        if 'Success' in data and data['Success'] and data['Success'] is not None:
            df = pd.DataFrame(data['Success'])
            # Check if dataframe is actually empty after creation
            if df.empty:
                print(f"API call successful but no data returned for {from_date} to {to_date}.")
                return pd.DataFrame()

            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            return df
        else:
            print(f"Error fetching option data: {data}")
            return pd.DataFrame()

    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()
# ---------------------------------------------------------
# END OF FIX
# ---------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", help="Run interactive setup to get a new session token.", action="store_true")
    args = parser.parse_args()

    # Authenticate and get the breeze client
    breeze = authenticate_icici(force_setup=args.setup)

    if args.setup:
        print("Setup complete. Session token stored.")
        exit()

    # Define the 1-month date range
    start_date_str = '2025-09-01'
    end_date_str = '2025-09-30'
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    mid_date = start_date + (end_date - start_date) / 2
    
    mid_date_str = mid_date.strftime('%Y-%m-%d')
    
    strike = 25300
    expiry = '2025-09-25'
    right = 'call'

    # Request 1: First half of the month
    df1 = fetch_option_data(breeze, start_date_str, mid_date_str, strike, expiry, right)

    # Request 2: Second half of the month
    df2 = fetch_option_data(breeze, (mid_date + timedelta(days=1)).strftime('%Y-%m-%d'), end_date_str, strike, expiry, right)

    dfs_to_concat = []
    if not df1.empty:
        dfs_to_concat.append(df1)
    if not df2.empty:
        dfs_to_concat.append(df2)

    if dfs_to_concat:
        # Concatenate the dataframes
        full_month_df = pd.concat(dfs_to_concat, ignore_index=True)
        
        # Save the complete DataFrame
        output_filename = 'test_option_data_1_MONTH.csv'
        full_month_df.to_csv(output_filename, index=False)
        print(f"Successfully fetched and saved data to {output_filename}")
    else:
        print("Could not fetch any data for the specified period.")