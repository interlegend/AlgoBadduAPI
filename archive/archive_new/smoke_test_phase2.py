"""
Smoke Test for Trader-Baddu Phase 2 Upgrade
Verifies that the core data pipeline is functional after the unification.
"""
from data_fetcher import get_nifty_ohlc, get_option_ohlc, set_tsl
from order_manager import get_atm_option_symbols

def run_smoke_test():
    print("[INFO] Running Phase 2 Smoke Test...")
    try:
        # 1. Initialize client and fetch NIFTY OHLC
        set_tsl()
        nifty_data = get_nifty_ohlc(interval=5)
        assert nifty_data is not None and not nifty_data.empty, "Failed to fetch NIFTY OHLC."
        print("[SUCCESS] Fetched NIFTY OHLC data.")
        
        # 2. Resolve ATM symbols
        spot = nifty_data['close'].iloc[-1]
        atm_symbols = get_atm_option_symbols(base_symbol="NIFTY", spot=spot)
        ce_sym = atm_symbols["CE_symbol"]
        assert ce_sym is not None, "Failed to resolve ATM CE symbol."
        print(f"[SUCCESS] Resolved ATM CE Symbol: {ce_sym}")

        # 3. Fetch OHLC for the resolved option symbol
        ce_data = get_option_ohlc(ce_sym, interval=5)
        assert ce_data is not None and not ce_data.empty, f"Failed to fetch OHLC for {ce_sym}."
        print(f"[SUCCESS] Fetched OHLC for ATM CE ({ce_sym}).")
        
        print("\n[SMOKE TEST PASSED] Core data pipeline is functional.")

    except Exception as e:
        print(f"\n[SMOKE TEST FAILED] An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_smoke_test()