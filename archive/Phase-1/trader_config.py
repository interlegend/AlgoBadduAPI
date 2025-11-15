#Trader Baddu:D
# Configuration for TB DHAN API ALGO
from typing import Dict, Set

CLIENT_ID = "1108149450"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMzcwMTU5LCJpYXQiOjE3NjAyODM3NTksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA4MTQ5NDUwIn0.47SL-blZsI4facP_zg0OwscBgBlJvevDox9RGgYDkA-pFzMc-R9G34HotYTKgNaYRJykyYqquwFUilEGOC5Q4Q"
                     
LOT_SIZE = 75
TP_POINTS = 15
SL_MULTIPLIER = 1.5
INTERVAL = "5m"
SLIPPAGE_TICKS = 1
BROKERAGE_RS = 20
TICK_VALUE = 1  # INR per point

# Canonical names and their known aliases
# This is the primary mapping used to resolve symbols and their properties.
ALIAS_MAP: Dict[str, Dict] = {
    "NIFTY": {
        "aliases": {"NIFTY", "NIFTY 50", "NIFTY50", "NIFTY INDEX"},
        "step": 50,
        "master_name": "NIFTY 50",
    },
    "BANKNIFTY": {
        "aliases": {"BANKNIFTY", "NIFTY BANK", "BANKNIFTY INDEX"},
        "step": 100,
        "master_name": "NIFTY BANK",
    },
    "FINNIFTY": {
        "aliases": {"FINNIFTY", "NIFTY FIN SERVICE", "FINNIFTY INDEX"},
        "step": 50,
        "master_name": "NIFTY FIN SERVICE",
    },
}

ICICI_API_KEY = "YOUR_API_KEY"
ICICI_API_SECRET = "YOUR_SECRET_KEY"


