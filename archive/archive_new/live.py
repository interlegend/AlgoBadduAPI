# live.py — Single source of truth for TradeHull client creation + injection
#Trader Baddu:D
# --------------------------------------------------------------------------
# What this file does:
#   1) Create and authenticate a single TradeHull client (`tsl`).
#   2) Inject that client into data_fetcher via set_tsl(tsl).
#
# How to authenticate:
#   - Preferred: use your existing, already-working method (whatever you used when
#     you saw "-----Logged into Dhan-----" in console).
#   - Below, we try multiple strategies in order:
#       A) If you have a helper that returns an authenticated client, call it.
#       B) Environment-based login (email/password or token) if your SDK supports.
#       C) As a last resort, instantiate the class and assume the SDK handles session.
#
#   Adjust the `make_tradehull_client()` function to match how YOU normally login.
#
# After `tsl` is ready, we call:
#   from data_fetcher import set_tsl
#   set_tsl(tsl)
#
# so the rest of your code (paper_trader, etc.) can call get_nifty_ohlc/get_option_ohlc.

import os
import sys

# 1) Import the SDK class (adjust if your module path differs)
try:
    from Dhan_Tradehull import Dhan_Tradehull as TH
except Exception as e:
    # Hard fail with a clear message
    raise ImportError(
        "Could not import Dhan_Tradehull. Ensure the package is installed "
        "and accessible in this Python env."
    ) from e

# 2) (Optional) If you keep a helper that returns an authenticated client,
#    import it here. Otherwise, edit make_tradehull_client() below to your flow.
# try:
#     from my_login_helper import build_tradehull_client  # your own helper
# except Exception:
#     build_tradehull_client = None

def make_tradehull_client():
    """
    Build and return an authenticated TradeHull client.

    *** IMPORTANT ***
    Replace/augment this with YOUR real login flow. A few templates are provided
    below — uncomment and adapt the one that matches your working setup.
    """
    # --- Template A: If you have a helper function somewhere ---
    # if build_tradehull_client is not None:
    #     return build_tradehull_client()

    # --- Template B: Email/Password login (if SDK supports) ---
    # email = os.environ.get("TRADEHULL_EMAIL")
    # password = os.environ.get("TRADEHULL_PASSWORD")
    # if email and password:
    #     th = TH()
    #     th.login(email=email, password=password)  # adjust to your SDK
    #     return th

    # --- Template C: API key/token (if SDK supports) ---
    # api_key = os.environ.get("TRADEHULL_API_KEY")
    # api_secret = os.environ.get("TRADEHULL_API_SECRET")
    # if api_key and api_secret:
    #     th = TH(api_key=api_key, api_secret=api_secret)  # adjust to your SDK
    #     # th.authenticate()  # if a separate step is required
    #     return th

    # --- Template D: Session reuse / local credential store ---
    # session_path = os.environ.get("TRADEHULL_SESSION_PATH", "tradehull_session.json")
    # if os.path.exists(session_path):
    #     th = TH()
    #     th.load_session(session_path)  # adjust if SDK uses a different name
    #     return th

    # --- Fallback: Bare instance (works if SDK reads credentials internally) ---
    # If your environment was already working without explicit args, this will too.
    th = TH()
    # If your SDK requires an explicit login step even with saved creds, do it here:
    # th.login_with_saved_session()  # example; adjust to your SDK
    return th

# 3) Create the client
tsl = make_tradehull_client()

# 4) Inject into data_fetcher so the whole project gets the same client
try:
    from data_fetcher import set_tsl
    set_tsl(tsl)
    # Uncomment to verify once:
    # print("[LIVE] Injected TradeHull client into data_fetcher.")
except Exception as e:
    # If this fails, make sure data_fetcher.py is on PYTHONPATH
    print(f"[LIVE-WARN] Could not inject client into data_fetcher: {e}", file=sys.stderr)

# (Optional) Expose convenience accessors (if other modules prefer importing from live)
def get_client():
    """Return the authenticated TradeHull client."""
    return tsl
