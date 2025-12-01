import requests
from config_live import UPSTOX_ACCESS_TOKEN

def test_search(symbol, segment):
    url = "https://api.upstox.com/v2/market/search/instrument"
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }
    params = {
        'instrument_key': symbol, # Try instrument_key? No, docs say 'search_key' usually?
        # Upstox API V2 Search: /market/search/instrument
        # Params: instrument_key (No), search_key (No).
        # Let's check standard params. usually 'q' or 'symbol'.
        # Docs: https://upstox.com/developer/api-documentation/search-instrument
        # Actually, correct param is 'instrument_key' for specific, but for search it's likely different.
        # Let's try 'search_string' again, but also check if endpoint is correct.
    }
    
    # Variation 1: search_string
    print(f"--- Testing search_string='{symbol}' segment='{segment}' ---")
    params = {'search_string': symbol, 'segment': segment}
    resp = requests.get(url, headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")

    # Variation 2: No segment
    print(f"--- Testing search_string='{symbol}' (No segment) ---")
    params = {'search_string': symbol}
    resp = requests.get(url, headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")

if __name__ == "__main__":
    test_search("CRUDEOIL", "MCX")
