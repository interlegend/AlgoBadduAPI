import websocket
import json
import logging
import threading
import time
import requests
import os
import sys

# Fix Windows Unicode
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

from config_live import UPSTOX_ACCESS_TOKEN

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG_WS")

def on_message(ws, message):
    if isinstance(message, bytes):
        logger.info(f"✅ RECEIVED BINARY DATA ({len(message)} bytes)")
        # Just print length to confirm flow
    else:
        logger.info(f"✅ RECEIVED TEXT DATA: {message}")

def on_error(ws, error):
    logger.error(f"❌ ERROR: {error}")

def on_close(ws, code, msg):
    logger.info(f"🔌 CLOSED: {code} - {msg}")

def on_open(ws):
    logger.info("🔓 OPENED")
    # Subscribe to NIFTY only for test
    instrument_key = "NSE_INDEX|Nifty 50"
    req = {
        "guid": "debug-uuid",
        "method": "sub",
        "data": {
            "mode": "full",
            "instrumentKeys": [instrument_key]
        }
    }
    logger.info(f"📤 SENDING SUB: {json.dumps(req)}")
    ws.send(json.dumps(req))

def get_auth_url():
    url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
    headers = {"Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    logger.info(f"🔑 AUTH RESPONSE: {resp.status_code} {resp.text}")
    if resp.status_code == 200:
        return resp.json()['data']['authorizedRedirectUri']
    return None

def main():
    ws_url = get_auth_url()
    if not ws_url:
        logger.error("Could not get WS URL")
        return

    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    
    # Run for 15 seconds then close
    t = threading.Thread(target=ws.run_forever)
    t.start()
    
    time.sleep(15)
    logger.info("🛑 TIME UP. Closing...")
    ws.close()
    t.join()

if __name__ == "__main__":
    main()
