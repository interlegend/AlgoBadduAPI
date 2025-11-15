# backtest.py
#Trader Baddu:D
import sys
print(">>> Python in use:", sys.executable)
print(">>> sys.path:", sys.path[:3])


import os
from strategy_v25 import run_backtest

if __name__ == "__main__":
    # Path to your data
    data_path = "C:\\Users\\sakth\\Desktop\\VSCODE\\TB DHAN API ALGO\\.vscode\\data\\nifty_5min_last_year.csv"
    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found: {data_path}")
    else:
        print(f"[DEBUG] Loading data from {data_path}")
        # Run the strategy backtest
        run_backtest(data_path)
