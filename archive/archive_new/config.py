#Trader Baddu:D
# Configuration for TB DHAN API ALGO
from typing import Dict, Set

CLIENT_ID = "1108149450"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMjg1NDk4LCJpYXQiOjE3NTc2OTM0OTgsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA4MTQ5NDUwIn0.4Y1lIGi-jKCJ8gbiBxoasql2VaSLtUaRjFiveIyje706tAg4ghjfo_D-g_0sJW-Eoc_APVmEW6k3uEo6oTACzw"
                     
LOT_SIZE = 75
TP_POINTS = 15
SL_MULTIPLIER = 1.5
INTERVAL = "5m"

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
