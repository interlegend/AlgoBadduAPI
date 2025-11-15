import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load the existing options data to get the correct timestamps
options_df = pd.read_csv('atm_candles_1_month.csv')
options_df['datetime'] = pd.to_datetime(options_df['timestamp'])
options_df = options_df.sort_values('datetime')

# Get unique timestamps from options data
timestamps = options_df['datetime'].unique()

# Create simulated NIFTY index data that matches the options timestamps
# We'll base this on typical NIFTY movements and levels seen in 2025

# Base NIFTY level (around 25000 in 2025)
base_level = 25000

# Create index data with realistic variations
index_data = []

for ts in timestamps:
    # Convert to naive datetime for calculations
    if ts.tzinfo is not None:
        ts_naive = ts.replace(tzinfo=None)
    else:
        ts_naive = ts
    
    # Create realistic NIFTY price variations based on time patterns
    # Get day of week and time of day for pattern-based variations
    day_of_week = ts_naive.weekday()
    hour = ts_naive.hour
    minute = ts_naive.minute
    
    # Base trend (weekly drift)
    week_num = ts_naive.isocalendar()[1]
    weekly_trend = (week_num - 40) * 50  # Small weekly drift
    
    # Daily pattern (intraday volatility)
    daily_pattern = np.sin((hour + minute/60) * np.pi / 12) * 30  # Intraday variations
    
    # Random noise
    noise = np.random.normal(0, 20)  # Random fluctuations
    
    # Create base close price
    close_price = base_level + weekly_trend + daily_pattern + noise
    
    # Open, high, low with realistic ranges
    open_price = close_price + np.random.normal(0, 5)
    range_size = np.random.uniform(20, 80)  # Realistic NIFTY range
    high_price = max(open_price, close_price) + range_size * 0.4
    low_price = min(open_price, close_price) - range_size * 0.6
    
    # Volume and OI (realistic values)
    volume = np.random.randint(1000000, 5000000)
    oi = np.random.randint(10000000, 50000000)
    
    index_data.append({
        'timestamp': ts.isoformat(),
        'index_open': round(open_price, 2),
        'index_high': round(high_price, 2),
        'index_low': round(low_price, 2),
        'index_close': round(close_price, 2),
        'index_volume': volume,
        'index_oi': oi
    })

# Create DataFrame
index_df = pd.DataFrame(index_data)
index_df = index_df.sort_values('timestamp')

# Save to CSV
index_df.to_csv('nifty_index_simulated_corrected.csv', index=False)

print(f"Created corrected NIFTY index data with {len(index_df)} records")
print("Date range:", index_df['timestamp'].min(), "to", index_df['timestamp'].max())
print("Sample of prices:")
print(index_df[['timestamp', 'index_close']].head(10))