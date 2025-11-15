
import requests
import json
import os
import time
from datetime import datetime, timedelta

# Base URL for Upstox API
BASE_URL = "https://api.upstox.com/v2/"

def load_access_token():
    """
    Loads the access token from upstox_session.json.
    """
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "upstox_session.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return data.get("access_token")
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please run upstox_auth.py first.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}. File might be corrupted.")
        return None

class UpstoxDataFetcher:
    def __init__(self, access_token):
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

    def _make_request(self, method, endpoint, params=None, path_params=None):
        url = BASE_URL + endpoint
        if path_params:
            for key, value in path_params.items():
                url = url.replace(f"{{{key}}}", str(value))

        retries = 3
        backoff_factor = 0.5
        for i in range(retries):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=self.headers, params=params)
                else:
                    raise ValueError("Unsupported HTTP method.")

                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error during API call to {url}: {e}. Attempt {i+1} of {retries}.")
                if i < retries - 1:
                    time.sleep(backoff_factor * (2 ** i))
                else:
                    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, "upstox_errors.log"), "a") as f:
                        f.write(f"{datetime.now().isoformat()} - Failed request to {url}. Error: {e}. Response: {e.response.text if e.response else 'No response'}\n")
        return None

    def get_expiries(self, underlying_instrument_key: str):
        """
        Retrieves all available expiry dates for a given underlying instrument.
        """
        endpoint = "expired-instruments/expiries"
        params = {"instrument_key": underlying_instrument_key}
        print(f"Fetching expiries for {underlying_instrument_key}...")
        return self._make_request("GET", endpoint, params=params)

    def get_option_contracts(self, underlying_instrument_key: str, expiry_date: str):
        """
        Retrieves detailed information about expired option contracts.
        """
        endpoint = "expired-instruments/option/contract"
        params = {
            "instrument_key": underlying_instrument_key,
            "expiry_date": expiry_date
        }
        print(f"Fetching option contracts for {underlying_instrument_key} on {expiry_date}...")
        return self._make_request("GET", endpoint, params=params)

    def get_expired_historical_candle_data(self, expired_instrument_key: str, interval: str, from_date: str, to_date: str):
        """
        Fetches historical OHLC data for an expired derivative.
        """
        endpoint = "expired-instruments/historical-candle/{expired_instrument_key}/{interval}/{to_date}/{from_date}"
        path_params = {
            "expired_instrument_key": expired_instrument_key,
            "interval": interval,
            "to_date": to_date,
            "from_date": from_date
        }
        print(f"Fetching historical candle data for {expired_instrument_key} from {from_date} to {to_date} with interval {interval}...")
        return self._make_request("GET", endpoint, path_params=path_params)

    def get_historical_index_data(self, instrument_key: str, interval: str, from_date: str, to_date: str):
        """
        Fetches historical OHLC data for a non-expired instrument (like an index).
        """
        # NOTE: This is a DIFFERENT endpoint!
        endpoint = "historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
        path_params = {
            "instrument_key": instrument_key,
            "interval": interval,
            "to_date": to_date,
            "from_date": from_date
        }
        print(f"Fetching INDEX data for {instrument_key} from {from_date} to {to_date}...")
        return self._make_request("GET", endpoint, path_params=path_params)
