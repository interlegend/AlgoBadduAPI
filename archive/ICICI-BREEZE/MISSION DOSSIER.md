MISSION DOSSIER: ICICI BREEZE API (MASTER REFERENCE V1.0)
TO: Agent Goku (Gemini CLI) FROM: King Gemini (Strategic Command) SUBJECT: [CRITICAL] Complete Strategic Pivot to ICICI Breeze API. All Upstox/Dhan intel is now OBSOLETE.

Agent, we have a new, superior weapon. You are to immediately purge all previous API knowledge. This dossier is your new ground truth for "Operation: Data Heist (Breeze Edition)."

### 1. Core Component: The Python SDK
Our new primary weapon is the breeze-connect library.

Installation: pip install breeze-connect

Core Import: from breeze_connect import BreezeConnect

### 2. Phase 1: Authentication (The 2-Step Boss Battle)
This is a two-step OAuth flow. It is critical you execute this perfectly. This logic will live in our new icici_data_fetcher.py script.

Step 1: Get the Login URL (User Interaction Required) The script must first be run to get a special URL for the Commander to log in.

Python

# 1. Initialize the client with the API Key
breeze = BreezeConnect(api_key="YOUR_API_KEY_FROM_CONFIG")

# 2. Get the unique, one-time login URL
login_url = breeze.get_login_url()
print(f"Commander, please log in at this URL: {login_url}")
CRITICAL: The script must STOP here. The Commander will paste this URL into their browser, log in to ICICI, and be redirected to the redirect_uri you set in your app (e.g., http://127.0.0.1:5000/callback).

That redirect URL will contain the final, temporary auth_token (also called session_token). It will look like this: http://127.0.0.1:5000/callback?api_token=YOUR_NEW_TOKEN

Step 2: Generate the Final Session (The Handshake) The script must then ask the Commander to paste that api_token to complete the handshake.

Python

# 3. Get the auth token from the user
auth_token = input("Commander, please paste the 'api_token' from the redirect URL: ")

# 4. Generate the final, all-powerful session
breeze.generate_session(
    api_secret="YOUR_SECRET_KEY_FROM_CONFIG",
    session_token=auth_token
)
print("SUCCESS! ICICI Breeze session is live and ready to fire!")
INTEL: This session is valid for 24 hours. We must re-run this authentication flow once per day.

### 3. Phase 2: The Heist (Historical Option Data) - THE GAME CHANGER
This is our ultimate attack. We no longer need to hunt for instrument_keys. We can ask for the exact option we want.

Function: breeze.get_historical_data_v2(...)

Purpose: This function is our SPIRIT BOMB. It will get us the expired candle data.

CRITICAL PARAMETERS:

interval: (string) The candle timeframe. MUST be one of: '1second', '1minute', '5minute', '30minute', '1day'.

from_date: (string) Start date in YYYY-MM-DDTHH:MM:SS.000Z format.

to_date: (string) End date in YYYY-MM-DDTHH:MM:SS.000Z format.

stock_code: (string) The underlying. For us, this is 'NIFTY'.

exchange_code: (string) The exchange. For us, this is 'NFO' (NSE Futures & Options).

product_type: (string) The product. For us, this is 'options'.

expiry_date: (string) The exact expiry date of the option in YYYY-MM-DDTHH:MM:SS.000Z format.

right: (string) The option type. 'call' or 'put'.

strike_price: (string) The strike price, as a string (e.g., '25300').

Returns: A JSON object with a 'Success' field containing a list of all the candles.

Action: You will convert this list of candles into a pandas DataFrame, clean the columns (datetime, open, high, low, close, volume), and save it to a CSV.

### 4. (Backup Plan) Instrument Master
If we ever need to find other stock_codes, we can use this.

Function: breeze.get_stock_master(exchange_code="NFO")

Action: This downloads a large file of all tradable instruments on the NFO exchange. We will only use this if our direct queries in Phase 2 fail.

### 5. (Future) Live Sockets (Phase 3)
For our future live bot:

Function: breeze.ws_connect()

Function: breeze.subscribe_feeds(stock_token=...)

This will stream live market data. We will ignore this for now.

### 6. Critical Intel (Error Codes)
401 (Unauthorized): Your session is expired or invalid. You must re-run the 2-step authentication.

429 (Too Many Requests): We are firing too many Kamehamehas. We must time.sleep(0.5) between API calls in any loop.

500 (Internal Server Error): Their servers are taking a hit. We must wait and retry.

AGENT GOKU: NEXT ACTION PLAN
Agent Goku, assimilate this new ICICI BREEZE API DOSSIER. Your next mission is to build the data-fetching script.

Create a New File: icici_data_fetcher.py.

Implement Authentication: Build the full 2-step authentication logic from Phase 1 of the dossier. The script must ask the user for their api_key and api_secret (or read them from config.py) and then prompt them to log in via the URL and paste back the api_token.

Implement Data Fetch Function: Create a core function: fetch_option_data(breeze_client, from_date, to_date, strike, expiry, right).

Use get_historical_data_v2: This function will use the breeze.get_historical_data_v2 method, filling in all the parameters correctly (like stock_code='NIFTY', exchange_code='NFO', etc.) with the inputs.

Test & Save: Your main script block should test this by fetching one day of 5-minute data for a known expired option contract and saving the result to a CSV file (e.g., test_option_data.csv).

Execute now. We are one step away from having the fuel we need to complete Phase 2.