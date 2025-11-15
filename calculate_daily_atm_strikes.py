import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time

# Load the NIFTY index data
print("Loading NIFTY index data...")
index_df = pd.read_csv('TB DHAN API ALGO/Phase-2/nifty_5min_last_month.csv')
index_df['datetime'] = pd.to_datetime(index_df['datetime'])

print(f"Loaded {len(index_df)} NIFTY index records")
print("Date range:", index_df['datetime'].min(), "to", index_df['datetime'].max())

# Extract daily closing prices at 3:30 PM for ATM strike calculation
print("Extracting daily closing prices at 3:30 PM...")
daily_closing_prices = []

# Group by date
index_df['date'] = index_df['datetime'].dt.date
for date, group in index_df.groupby('date'):
    # Find the 3:30 PM closing price (or the last price of the day if 3:30 doesn't exist)
    day_end = group[group['datetime'].dt.time >= time(15, 25)]
    if not day_end.empty:
        closing_row = day_end.iloc[-1]  # Last 5-minute candle of the day
        daily_closing_prices.append({
            'date': date,
            'datetime': closing_row['datetime'],
            'close_price': closing_row['close']
        })
    else:
        # If no 3:30 data, take the last available timestamp of the day
        closing_row = group.iloc[-1]
        daily_closing_prices.append({
            'date': date,
            'datetime': closing_row['datetime'],
            'close_price': closing_row['close']
        })

daily_df = pd.DataFrame(daily_closing_prices)
print(f"Extracted {len(daily_df)} daily closing prices")
print("Sample daily closing prices:")
print(daily_df.head(10))

# Calculate ATM strikes for each day (round to nearest 50)
print("Calculating ATM strikes for each day...")
daily_df['atm_strike'] = (daily_df['close_price'] / 50).round() * 50
daily_df['atm_strike'] = daily_df['atm_strike'].astype(int)

print("Daily ATM strikes:")
print(daily_df[['date', 'close_price', 'atm_strike']])

# Create a mapping from date to ATM strike
date_to_atm_strike = dict(zip(daily_df['date'], daily_df['atm_strike']))

# Save this mapping for use in the backtester
print("Saving date-to-ATM-strike mapping...")
daily_df.to_csv('daily_atm_strikes.csv', index=False)

print("ATM strike calculation completed successfully!")
print(f"Date range covered: {daily_df['date'].min()} to {daily_df['date'].max()}")
print(f"ATM strikes range: {daily_df['atm_strike'].min()} to {daily_df['atm_strike'].max()}")