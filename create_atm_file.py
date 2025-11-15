
import pandas as pd
from datetime import datetime, timedelta, time

def create_corrected_atm_file():
    try:
        nifty_df = pd.read_csv("C:/Users/sakth/Desktop/VSCODE/TB DHAN API ALGO/Phase-2/nifty_5min_last_month.csv")
        nifty_df['datetime'] = pd.to_datetime(nifty_df['datetime'])
        if nifty_df['datetime'].dt.tz is None:
            nifty_df['datetime'] = nifty_df['datetime'].dt.tz_localize('Asia/Kolkata')
        else:
            nifty_df['datetime'] = nifty_df['datetime'].dt.tz_convert('Asia/Kolkata')
        nifty_df.set_index('datetime', inplace=True)
        print("Successfully loaded and processed NIFTY index data.")
    except FileNotFoundError:
        print("FATAL: NIFTY index data file not found. Exiting.")
        return

    try:
        options_df = pd.read_csv("C:/Users/sakth/Desktop/VSCODE/atm_candles_1_month.csv")
        options_df['datetime'] = pd.to_datetime(options_df['timestamp'])
        if options_df['datetime'].dt.tz is None:
            options_df['datetime'] = options_df['datetime'].dt.tz_localize('Asia/Kolkata')
        else:
            options_df['datetime'] = options_df['datetime'].dt.tz_convert('Asia/Kolkata')
        print("Successfully loaded and processed options data.")
    except FileNotFoundError:
        print("FATAL: Options data file not found. Exiting.")
        return

    all_dates = nifty_df.index.date
    unique_dates = sorted(list(set(all_dates)))
    thursdays = [d for d in unique_dates if d.weekday() == 3]

    corrected_dfs = []

    for expiry_date in thursdays:
        print(f"\n--- Processing Expiry Week of: {expiry_date} ---")
        
        nifty_close = None
        check_date = None
        for i in range(8):
            current_check_date = expiry_date - timedelta(days=7+i)
            if current_check_date in unique_dates:
                prev_expiry_day_data = nifty_df[nifty_df.index.date == current_check_date]
                if not prev_expiry_day_data.empty:
                    eod_candle = prev_expiry_day_data.iloc[-1:]
                    if not eod_candle.empty:
                        nifty_close = eod_candle.iloc[0]['close']
                        check_date = current_check_date
                        print(f"Found EOD data for {check_date}.")
                        break
        
        if nifty_close is None:
            print(f"Could not find recent EOD NIFTY data for week of {expiry_date}. Skipping week.")
            continue

        atm_strike = int(round(nifty_close / 50) * 50)
        print(f"NIFTY close on {check_date} was {nifty_close}. ATM Strike for this week is: {atm_strike}")

        # Filter the options data for this week and this strike
        week_start_date = expiry_date - timedelta(days=6)
        
        weekly_options_df = options_df[
            (options_df['datetime'].dt.date >= week_start_date) &
            (options_df['datetime'].dt.date <= expiry_date) &
            (options_df['strike_price'] == atm_strike)
        ]

        if not weekly_options_df.empty:
            print(f"Found {len(weekly_options_df)} candles for strike {atm_strike} for the week of {expiry_date}")
            corrected_dfs.append(weekly_options_df)
        else:
            print(f"No data found for strike {atm_strike} for the week of {expiry_date}")

    if corrected_dfs:
        final_df = pd.concat(corrected_dfs, ignore_index=True)
        output_filename = "atm_candles_1_month_CORRECTED.csv"
        final_df.to_csv(output_filename, index=False)
        print(f"\nSUCCESS! 🔥 Successfully saved corrected ATM data to {output_filename}")
    else:
        print("\nNo data was corrected or saved.")

if __name__ == "__main__":
    create_corrected_atm_file()
