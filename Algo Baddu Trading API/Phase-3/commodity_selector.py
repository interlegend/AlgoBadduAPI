"""
Commodity Key Selector (MCX)
Dynamically finds the active Future Contract for Crude Oil, Nat Gas, etc.
Method: Downloads Upstox Master Instrument File (MCX.json.gz) and filters locally.
"""

import requests
import logging
import gzip
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class CommodityKeySelector:
    def __init__(self, access_token=None):
        # Access token not needed for public assets URL
        self.master_url = "https://assets.upstox.com/market-quote/instruments/exchange/MCX.json.gz"

    def get_current_future(self, symbol):
        """
        Find the nearest active Future contract for a given symbol (e.g. CRUDEOIL).
        Returns: (instrument_key, lot_size, expiry_date)
        """
        try:
            logger.info(f"📥 Downloading MCX Master Contract list from Upstox...")
            response = requests.get(self.master_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to download master list: {response.status_code}")
                return None, None, None
            
            # Decompress and Parse
            content = gzip.decompress(response.content)
            instruments = json.loads(content)
            
            logger.info(f"✅ Loaded {len(instruments)} MCX instruments. Filtering for {symbol}...")
            
            # Filter for Futures
            # Upstox Master Format keys: 'trading_symbol', 'instrument_type', 'expiry', 'lot_size', 'instrument_key'
            # Symbol example: "CRUDEOIL 19 DEC 25" (Check format) or just "CRUDEOIL" prefix
            
            futures = []
            today = datetime.now().date()
            
            for item in instruments:
                # Check if it's a Future
                if item.get('instrument_type') != 'FUT':
                    continue
                
                trading_symbol = item.get('trading_symbol', '')
                
                # Check if symbol matches (e.g., "CRUDEOIL")
                # Trading symbol format: "CRUDEOILM 19 FEB 24" or "CRUDEOIL 18 DEC 24"
                # We check if it starts with the symbol name
                if not trading_symbol.startswith(symbol):
                    continue
                
                # Parse Expiry
                expiry_ts = item.get('expiry') # Unix timestamp in ms? Or string?
                # Upstox JSON usually uses 'expiry' as a timestamp (milliseconds)
                
                expiry_date = None
                if expiry_ts:
                    try:
                        # Convert ms timestamp to date
                        expiry_date = datetime.fromtimestamp(int(expiry_ts)/1000).date()
                    except:
                        pass
                
                if expiry_date and expiry_date >= today:
                    futures.append({
                        'key': item.get('instrument_key'),
                        'expiry': expiry_date,
                        'lot_size': item.get('lot_size'),
                        'symbol': trading_symbol
                    })
            
            if not futures:
                logger.error(f"❌ No active futures found for {symbol}")
                return None, None, None
            
            # Sort: Nearest expiry first
            futures.sort(key=lambda x: x['expiry'])
            
            target = futures[0]
            logger.info(f"✅ Found Active Contract: {target['symbol']}")
            logger.info(f"   Key: {target['key']} | Expiry: {target['expiry']} | Lot: {target['lot_size']}")
            
            return target['key'], target['lot_size'], target['expiry']

        except Exception as e:
            logger.error(f"💥 Exception in CommoditySelector: {e}", exc_info=True)
            return None, None, None
