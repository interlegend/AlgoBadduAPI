
# === Imports ===
from data_fetcher import get_live_data
from strategy_v25 import add_indicators, generate_signals
from order_manager import get_atm_option_symbol, place_option_order


LOT_SIZE = 75  # Nifty lot size

def run():
    df = get_live_data()
    df = add_indicators(df)
    signals = generate_signals(df)
    for sig in signals:
        spot = sig["entry_price"]
        side = sig["side"]
        option_symbol = get_atm_option_symbol(spot, side, expiry="28AUG24")
        place_option_order(option_symbol, side="BUY", qty=LOT_SIZE)
        print(f"🎯 Signal: {side} at {spot} → Buying {option_symbol}")
    return signals

if __name__ == "__main__":
    run()
