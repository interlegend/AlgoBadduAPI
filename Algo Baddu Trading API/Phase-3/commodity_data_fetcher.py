"""
Commodity Data Fetcher (MCX)
Specialized fetcher for Crude Oil and Natural Gas Futures using Upstox V3 API.
"""

import requests
import pandas as pd
import logging
import os
import urllib.parse
from datetime import datetime, timedelta
import sys

# Add parent directory to path to import config_live and selectors
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_live import UPSTOX_ACCESS_TOKEN, PROJECT_ROOT
from commodity_selector import CommodityKeySelector

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class CommodityDataFetcher:
    def __init__(self, access_token):
        self.access_token = access_token
        self.key_selector = CommodityKeySelector(access_token)
        self.base_url = "https://api.upstox.com/v3/historical-candle"

    def fetch_recent_history(self, symbol, days=5, interval="5"):
        """
        Fetch recent historical candles for the active future of a symbol.
        
        Args:
            symbol: 'CRUDEOIL' or 'NATURALGAS'
            days: Number of days to look back
            interval: Candle interval in minutes ('1', '5', '30')
        
        Returns:
            pd.DataFrame with historical data
        """
        # 1. Get Active Key
        key, lot, expiry = self.key_selector.get_current_future(symbol)
        if not key:
            logger.error(f"❌ Could not find active future for {symbol}")
            return None

        logger.info(f"✅ Active Contract: {symbol} | Key: {key} | Expiry: {expiry}")

        # 2. Prepare Dates
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days)
        
        # 3. Construct V3 API URL
        # /v3/historical-candle/{instrumentKey}/{unit}/{interval}/{to_date}/{from_date}
        # unit = 'minutes'
        encoded_key = urllib.parse.quote(key, safe='')
        url = f"{self.base_url}/{encoded_key}/minutes/{interval}/{to_date}/{from_date}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

        logger.info(f"⏳ Fetching data from {from_date} to {to_date}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                candles = data.get("candles", [])
                
                if not candles:
                    logger.warning("⚠️ No candles returned.")
                    return pd.DataFrame()
                
                # Parse Candles
                # Format: [timestamp, open, high, low, close, volume, oi]
                parsed_data = []
                for c in candles:
                    parsed_data.append({
                        'timestamp': pd.to_datetime(c[0]).tz_localize(None), # Force naive for compatibility
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': int(c[5]),
                        'oi': int(c[6]) if len(c) > 6 else 0
                    })
                
                df = pd.DataFrame(parsed_data)
                df.sort_values('timestamp', inplace=True)
                df.reset_index(drop=True, inplace=True)
                
                logger.info(f"✅ Fetched {len(df)} candles.")
                return df
                
            else:
                logger.error(f"❌ API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"💥 Exception fetching data: {e}", exc_info=True)
            return None

    def save_to_csv(self, df, symbol):
        if df is not None and not df.empty:
            filename = f"{symbol}_history_{datetime.now().strftime('%Y%m%d')}.csv"
            path = os.path.join(PROJECT_ROOT, "Phase-3", filename)
            df.to_csv(path, index=False)
            logger.info(f"💾 Saved to: {path}")
        else:
            logger.warning("⚠️ Nothing to save.")

def main():
    print("🚀 COMMODITY DATA FETCHER (MCX)")
    
    fetcher = CommodityDataFetcher(UPSTOX_ACCESS_TOKEN)
    
    # Example: Fetch Crude Oil
    df = fetcher.fetch_recent_history("CRUDEOIL", days=5)
    fetcher.save_to_csv(df, "CRUDEOIL")
    
    # Example: Fetch Natural Gas
    # df_ng = fetcher.fetch_recent_history("NATURALGAS", days=5)
    # fetcher.save_to_csv(df_ng, "NATURALGAS")

if __name__ == "__main__":
    main()
