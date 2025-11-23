import os
import json
import webbrowser
from datetime import datetime
from fyers_apiv3 import fyersModel


# Fyers App Config (set your own values here)
client_id = "77Z3CHKI1N-100"  # Updated App ID
secret_key = "1TN94FLXWF"  # Updated Secret Key
redirect_uri = "https://httpbin.org/get"  # Updated Redirect URI

token_file = "token.json"

def save_token(token_data):
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)
    print("✅ Tokens saved successfully!")

def load_token():
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            try:
                return json.load(f)
            except:
                print("❌ token.json is invalid.")
    return None

def generate_auth_link():
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code",
        state=str(datetime.now().timestamp())
    )
    auth_url = session.generate_authcode()
    print("🔗 Login URL:", auth_url)
    webbrowser.open(auth_url)
    return session

def get_tokens_from_code(auth_code):
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    session.set_token(auth_code)  # REQUIRED in latest SDK
    response = session.generate_token()
    print("📥 Token response:", response)

    if "access_token" in response:
        save_token(response)
        return response
    else:
        raise Exception("❌ Token generation failed:", response)

def refresh_token():
    tokens = load_token()
    if not tokens or "refresh_token" not in tokens:
        raise Exception("❌ Refresh token not found. Please login again.")
    
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        grant_type="refresh_token",
        response_type="code"
    )
    session.set_token(tokens["refresh_token"])
    refreshed = session.generate_token()
    print("♻️ Refreshed response:", refreshed)

    if "access_token" in refreshed:
        save_token(refreshed)
        return refreshed
    else:
        raise Exception("❌ Refresh failed:", refreshed)

if __name__ == "__main__":
    print("🔐 Starting Fyers login flow")
    session = generate_auth_link()
    code = input("Paste the code here: ").strip()
    get_tokens_from_code(code)
