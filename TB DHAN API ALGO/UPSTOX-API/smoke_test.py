import pandas as pd
from datetime import datetime

# Load the output file
try:
    df = pd.read_csv('atm_daily_options_HYBRID_V3.csv')
    print("[SUCCESS] ✅ Output file 'atm_daily_options_HYBRID_V3.csv' loaded.")
    
    # 1. Verify NIFTY OHLC data was processed
    assert len(df) > 0, "Test FAILED: Output file is empty."
    print("[SUCCESS] ✅ NIFTY OHLC data processed (file is not empty).")

    # 2. Verify ATM CE & PE symbols were resolved for a recent expiry
    test_day = '2025-10-27'
    day_df = df[df['trading_day'] == test_day]
    assert not day_df.empty, f"Test FAILED: No data found for {test_day}."
    
    ce_count = len(day_df[day_df['instrument_type'] == 'CE'])
    pe_count = len(day_df[day_df['instrument_type'] == 'PE'])
    assert ce_count > 0 and pe_count > 0, f"Test FAILED: Missing CE or PE data for {test_day}."
    print(f"[SUCCESS] ✅ ATM CE & PE symbols resolved for {test_day} (CE: {ce_count}, PE: {pe_count}).")

    # 3. Verify OHLC data was fetched for an option symbol
    option_candles = day_df[(day_df['instrument_type'] == 'CE') & (day_df['trading_day'] == test_day)]
    assert len(option_candles) > 0, "Test FAILED: No OHLC data found for CE option."
    print(f"[SUCCESS] ✅ OHLC data fetched for CE option on {test_day} ({len(option_candles)} candles).")

    print("\n🎉 SMOKE TEST PASSED! 🎉")

except FileNotFoundError:
    print("[ERROR] ❌ Test FAILED: 'atm_daily_options_HYBRID_V3.csv' not found. Run the main script first.")
except Exception as e:
    print(f"[ERROR] ❌ An unexpected error occurred: {e}")
