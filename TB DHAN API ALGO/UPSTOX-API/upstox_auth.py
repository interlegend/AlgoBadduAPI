
import requests
import urllib.parse
import json
import os
import config  # Use relative import if config.py is in the same folder

def get_access_token():
    """
    Performs the OAuth 2.0 flow to get an access token from Upstox.
    """
    # Step 1: Generate the authorization URL
    auth_params = {
        "client_id": config.API_KEY,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": "code"
    }
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?{urllib.parse.urlencode(auth_params)}"

    print("Please go to the following URL, log in, and authorize the application:")
    print(auth_url)
    print("\n" + "="*80 + "\n")

    # Step 2: Get the authorization code from the redirect URL
    redirect_url = input("Please paste the full redirect URL here: ")
    parsed_url = urllib.parse.urlparse(redirect_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    if "code" not in query_params:
        print("Error: Could not find 'code' in the redirect URL.")
        return

    auth_code = query_params["code"][0]
    print(f"\nSuccessfully extracted authorization code: {auth_code}\n")

    # Step 3: Exchange the authorization code for an access token
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    token_headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    token_data = {
        "code": auth_code,
        "client_id": config.API_KEY,
        "client_secret": config.API_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    print("Requesting access token...")
    try:
        response = requests.post(token_url, headers=token_headers, data=token_data)
        response.raise_for_status()  # Raise an exception for bad status codes

        token_response = response.json()

        # Step 4: Save the access token (Fixed relative path)
        script_dir = os.path.dirname(__file__)  # Get the script's directory
        file_path = os.path.join(script_dir, "upstox_session.json")

        with open(file_path, "w") as f:
            json.dump(token_response, f, indent=4)

        print(f"\nSaving token to: {file_path}\n")

        print("\n" + "="*80)
        print("Access token received and saved to upstox_session.json successfully!")
        print(f"Access Token: {token_response.get('access_token')}")
        print("="*80 + "\n")

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred while requesting the access token: {e}")
        if e.response:
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    get_access_token()
