
import sys
import os
import logging

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)

from atm_selector import ATMSelector

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI0S0NNR1YiLCJqdGkiOiI2OTJiZjZhMmJhYzQ4MDMwYmFiODM2MTQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzY0NDg4ODY2LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NjQ1NDAwMDB9.E_MCA5haoBB3lbY-pXabVGdQXHhyrIVCFzBmONNCoMk"

def test():
    selector = ATMSelector(ACCESS_TOKEN)
    print("Testing get_nifty_spot...")
    spot = selector.get_nifty_spot()
    print(f"Spot: {spot}")
    
    if spot:
        print("Testing get_atm_keys...")
        atm, ce, pe = selector.get_atm_keys(spot)
        print(f"ATM: {atm}, CE: {ce}, PE: {pe}")
    else:
        print("Could not fetch spot, maybe market closed or token invalid?")
        # Try with fake spot
        print("Testing with fake spot 24000...")
        atm, ce, pe = selector.get_atm_keys(24000)
        print(f"ATM: {atm}, CE: {ce}, PE: {pe}")

if __name__ == "__main__":
    test()
