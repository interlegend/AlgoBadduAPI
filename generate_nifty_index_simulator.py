import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# Load the options data
options_df = pd.read_csv('atm_candles_1_month.csv')
options_df['timestamp'] = pd.to_datetime(options_df['timestamp'])
options_df = options_df.sort_values(by='timestamp')

# Define IST timezone
IST = pytz.timezone("Asia/Kolkata")

# Create a function to estimate NIFTY index value based on timestamp and known ATM strikes
def estimate_nifty_index(timestamp):
    """
    Estimate the NIFTY index value for a given timestamp based on known ATM strikes.
    This uses the fact that ATM strike = round(NIFTY_price / 50) * 50
    So NIFTY_price ≈ ATM_strike ± some value around the target ATM strike
    """
    # Define the known ATM strikes for each expiry week based on the fetcher log
    # From the logs: 
    # - Week starting 2024-09-26 (expiry 2024-10-03): ATM was 26200
    # - Week starting 2024-10-03 (expiry 2024-10-10): ATM was 25250  
    # - Week starting 2024-10-10 (expiry 2024-10-17): ATM was 25000
    # - Week starting 2024-10-17 (expiry 2024-10-24): ATM was 24750
    
    # Create a mapping of weeks to ATM strikes
    week_atm_mapping = {
        (datetime(2024, 9, 26).replace(tzinfo=None), datetime(2024, 10, 3).replace(tzinfo=None)): 26200,
        (datetime(2024, 10, 3).replace(tzinfo=None), datetime(2024, 10, 10).replace(tzinfo=None)): 25250,
        (datetime(2024, 10, 10).replace(tzinfo=None), datetime(2024, 10, 17).replace(tzinfo=None)): 25000,
        (datetime(2024, 10, 17).replace(tzinfo=None), datetime(2024, 10, 24).replace(tzinfo=None)): 24750
    }
    
    # Convert timestamp to naive datetime for comparison
    if timestamp.tzinfo is not None:
        timestamp_naive = timestamp.replace(tzinfo=None)
    else:
        timestamp_naive = timestamp
    
    # Find which week the timestamp falls in
    for (start_week, end_week), atm_strike in week_atm_mapping.items():
        if start_week <= timestamp_naive <= end_week:
            # Estimate NIFTY around the ATM strike with some realistic variation
            # Use the actual closes from options to estimate realistic movements
            # For now, let's make a simple estimate around the ATM with realistic daily variation
            base_value = atm_strike
            # Add some variation based on time within the week
            day_in_week = (timestamp_naive - start_week).days
            hour_of_day = timestamp_naive.hour
            minute_of_hour = timestamp_naive.minute
            
            # Create a realistic variation using a combination of daily and intraday trends
            daily_variation = (day_in_week - 3) * 15  # Some daily movement around center
            intraday_variation = np.sin((hour_of_day + minute_of_hour/60) * np.pi / 24) * 30  # Intraday variation
            
            estimated_nifty = base_value + daily_variation + intraday_variation
            return round(estimated_nifty, 2)
    
    # If timestamp doesn't fall in any known week, return a default estimate
    return 25000.0

# Apply the function to create a simulated NIFTY index dataset
timestamps = options_df['timestamp'].unique()
nifty_data = []

for ts in timestamps:
    estimated_index = estimate_nifty_index(ts)
    nifty_data.append({
        'timestamp': ts,
        'index_open': estimated_index,
        'index_high': estimated_index + np.random.uniform(5, 15),
        'index_low': estimated_index - np.random.uniform(5, 15),
        'index_close': estimated_index,
        'index_volume': np.random.randint(1000000, 5000000),
        'index_oi': np.random.randint(10000000, 50000000)
    })

# Create the simulated index dataframe
index_df = pd.DataFrame(nifty_data)
index_df = index_df.sort_values('timestamp')

# Save to CSV
index_df.to_csv('nifty_index_simulated.csv', index=False)

print(f"Created simulated NIFTY index data with {len(index_df)} records")
print("First few records:")
print(index_df.head())
print("Date range:", index_df['timestamp'].min(), "to", index_df['timestamp'].max())