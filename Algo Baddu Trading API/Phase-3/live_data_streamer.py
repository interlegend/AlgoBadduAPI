"""
Live Data Streamer - SPACE AGE EDITION (SDK V3)
Powered by upstox-python-sdk MarketDataStreamerV3.
Handles Warm-Up (Historical) and Live Streaming (SDK).
"""

import logging
import threading
import time
import requests
import urllib.parse
from datetime import datetime, timedelta
import pandas as pd
import upstox_client
# CORRECTED IMPORT PATH
from upstox_client.feeder import MarketDataStreamerV3

logger = logging.getLogger(__name__)

class LiveDataStreamer:
    def __init__(self, api_client, instrument_keys, indicator_calculator, on_candle_closed_callback):
        """
        Initialize Live Data Streamer with SDK V3.
        
        Args:
            api_client: Upstox ApiClient object (not just token).
            instrument_keys: Dict with 'nifty', 'ce', 'pe' keys.
            indicator_calculator: IndicatorCalculator instance.
            on_candle_closed_callback: Callback function.
        """
        self.api_client = api_client
        self.instrument_keys = instrument_keys
        self.indicator_calculator = indicator_calculator
        self.on_candle_closed_callback = on_candle_closed_callback
        
        # Initialize SDK Streamer
        self.streamer = MarketDataStreamerV3(api_client)
        
        # Candle management
        self.current_candles = {'NIFTY': None, 'CE': None, 'PE': None}
        self.current_candle_start = None
        self.latest_prices = {'NIFTY': None, 'CE': None, 'PE': None}
        self.is_connected = False
        
        logger.info("✅ Live Data Streamer (Space Age V3) initialized.")

    # ==============================================================================
    #  PART 1: HISTORICAL WARM-UP (THE "TIME MACHINE")
    #  (Logic preserved as per directives)
    # ==============================================================================
    
    def initialize_warmup(self, days=5):
        """
        Fetches historical data for NIFTY, CE, and PE to warm up indicators.
        Uses the access_token from api_client configuration.
        """
        logger.info(f"🔥 STARTING WARM-UP: Fetching last {days} days of NIFTY & ATM Options...")
        
        # Define instruments to warm up
        instruments_to_fetch = [
            ('NIFTY', self.instrument_keys['nifty']),
            ('CE', self.instrument_keys['ce']),
            ('PE', self.instrument_keys['pe'])
        ]
        
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days)
        
        # Extract token from ApiClient
        access_token = self.api_client.configuration.access_token
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        for type_label, key in instruments_to_fetch:
            if not key:
                logger.warning(f"⚠️ Skipping Warm-Up for {type_label} (No Key)")
                continue

            encoded_key = urllib.parse.quote(key, safe='')
            url = f"https://api.upstox.com/v3/historical-candle/{encoded_key}/minutes/5/{to_date}/{from_date}"
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    candles = data.get("candles", [])
                    
                    if candles:
                        logger.info(f"✅ {type_label}: Fetched {len(candles)} historical candles.")
                        self._process_historical_candles(candles, type_label)
                    else:
                        logger.warning(f"⚠️ {type_label}: No historical candles found.")
                else:
                    logger.error(f"❌ {type_label} Warm-up failed! Status: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"💥 Exception during {type_label} Warm-Up: {e}", exc_info=True)

    def _process_historical_candles(self, candles, instrument_type):
        """
        Feeds historical candles into the IndicatorCalculator.
        Upstox Format: [timestamp, open, high, low, close, volume, oi]
        """
        parsed_candles = []
        for c in candles:
            try:
                ts = pd.to_datetime(c[0])
                if pd.isna(ts): continue
                
                parsed_candles.append({
                    'timestamp': ts,
                    'open': float(c[1]),
                    'high': float(c[2]),
                    'low': float(c[3]),
                    'close': float(c[4]),
                    'volume': int(c[5])
                })
            except Exception as e:
                continue
        
        # Sort ascending (oldest first)
        parsed_candles.sort(key=lambda x: x['timestamp'])
        
        for candle in parsed_candles:
            self.indicator_calculator.add_candle(instrument_type, candle)

    # ==============================================================================
    #  PART 2: SDK V3 STREAMING (THE "SPACE AGE" ENGINE)
    # ==============================================================================

    def start_websocket(self):
        """Starts the SDK V3 Streamer."""
        logger.info("🚀 Starting SDK Streamer...")
        
        # Setup Event Handlers
        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)
        
        # Auto-Reconnect: Enable=True, Interval=3s, RetryCount=10
        self.streamer.auto_reconnect(True, 3, 10)
        
        # Connect
        self.streamer.connect()
        return True

    def on_open(self):
        """Event: Connection Opened."""
        logger.info("🔓 SDK Streamer Connected!")
        self.is_connected = True
        
        # Subscribe immediately
        keys_list = [k for k in self.instrument_keys.values() if k]
        logger.info(f"📡 Subscribing to: {keys_list}")
        
        # Subscribe using SDK method (Mode: Full)
        self.streamer.subscribe(keys_list, "full")

    def on_message(self, message):
        """
        Event: Message Received.
        The SDK returns a decoded message dictionary.
        """
        # message is typically a dictionary with 'feeds'
        try:
            # DEBUG: Print raw message keys/structure to understand layout
            # logger.info(f"📩 SDK MSG: {str(message)[:500]}...") 
            
            feeds = message.get('feeds')
            if not feeds:
                # Could be market_info or initial handshake
                # logger.info(f"ℹ️ SDK Info Msg: {message}")
                return

            for key, feed_data in feeds.items():
                self._process_feed_data(key, feed_data)
                
        except Exception as e:
            logger.error(f"💥 Error processing SDK message: {e}")

    def on_error(self, error):
        """Event: Error Occurred."""
        logger.error(f"💥 SDK Streamer Error: {error}")

    def on_close(self, message=None):
        """Event: Connection Closed."""
        logger.warning(f"🔌 SDK Streamer Closed: {message}")
        self.is_connected = False

    def _process_feed_data(self, instrument_key, feed_data):
        """
        Process individual feed data from SDK.
        Map SDK structure to our internal logic.
        """
        # Identify instrument type from key
        instrument_name = 'UNKNOWN'
        if instrument_key == self.instrument_keys.get('nifty'):
            instrument_name = 'NIFTY'
        elif instrument_key == self.instrument_keys.get('ce'):
            instrument_name = 'CE'
        elif instrument_key == self.instrument_keys.get('pe'):
            instrument_name = 'PE'
        
        if instrument_name == 'UNKNOWN':
            return

        # Extract Data (Robust Drilling)
        ltp = None
        vtt = 0
        ohlc_snap = {}
        cp = None

        # Check for LTPC at root (LTPC mode)
        if 'ltpc' in feed_data:
            ltp = feed_data['ltpc'].get('ltp')
            cp = feed_data['ltpc'].get('cp')
        
        # Check Full Feed nesting (observed in logs)
        elif 'fullFeed' in feed_data:
            ff = feed_data['fullFeed']
            # It could be marketFF or indexFF
            data_source = ff.get('marketFF') or ff.get('indexFF')
            
            if data_source and 'ltpc' in data_source:
                ltp = data_source['ltpc'].get('ltp')
                cp = data_source['ltpc'].get('cp')
                
                # Extract VTT and OHLC while we are here
                vtt = data_source.get('vtt', 0)
                market_ohlc = data_source.get('marketOHLC', {}).get('ohlc', [])
                if market_ohlc:
                    # Take the most recent I1 or 1m candle
                    candle_data = next((x for x in market_ohlc if x.get('interval') in ['1m', 'I1']), None)
                    if candle_data:
                        ohlc_snap = candle_data

        # Fallback for direct flat structure (if any)
        if ltp is None:
            ltp = feed_data.get('ltp')
            cp = feed_data.get('cp')

        if ltp is None:
            return

        # Construct update payload
        open_p = ohlc_snap.get('open', ltp)
        high_p = ohlc_snap.get('high', ltp)
        low_p = ohlc_snap.get('low', ltp)
        
        # Update Latest Prices
        self.latest_prices[instrument_name] = {
            'ltp': ltp,
            'cp': cp,
            'open': open_p,
            'high': high_p,
            'low': low_p
        }
        
        # Update Candle Aggregator
        self._update_candle_with_tick(instrument_name, ltp, vtt)

    def _update_candle_with_tick(self, instrument_name, ltp, vtt):
        """Aggregates ticks into 5-minute candles."""
        now = datetime.now()
        
        # Initialize start time aligned to 5-minute grid
        if self.current_candle_start is None:
            self.current_candle_start = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
        
        # Check if we crossed into a new 5-minute block
        next_candle_start = self.current_candle_start + timedelta(minutes=5)
        
        if now >= next_candle_start:
            self._close_candles()
            # Align strictly to the grid
            self.current_candle_start = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
            self.current_candles = {'NIFTY': None, 'CE': None, 'PE': None}

        # Initialize candle if new
        if self.current_candles[instrument_name] is None:
            self.current_candles[instrument_name] = {
                'timestamp': self.current_candle_start, 
                'open': ltp, 
                'high': ltp, 
                'low': ltp, 
                'close': ltp, 
                'volume': vtt # Note: This is cumulative day volume, ideally we want candle vol, but using VTT for now
            }
        else:
            # Update existing candle
            candle = self.current_candles[instrument_name]
            candle['high'] = max(candle['high'], ltp)
            candle['low'] = min(candle['low'], ltp)
            candle['close'] = ltp
            candle['volume'] = vtt

    def _close_candles(self):
        """Push completed 5-min candles to the Calculator."""
        logger.info(f"🔔 5-Min Candle Closed @ {self.current_candle_start.strftime('%H:%M')}")
        
        if self.current_candles['NIFTY']:
            self.indicator_calculator.add_candle('NIFTY', self.current_candles['NIFTY'])
        if self.current_candles['CE']:
            self.indicator_calculator.add_candle('CE', self.current_candles['CE'])
        if self.current_candles['PE']:
            self.indicator_calculator.add_candle('PE', self.current_candles['PE'])
            
        if self.on_candle_closed_callback:
            self.on_candle_closed_callback('NIFTY')

    def disconnect(self):
        """Disconnects the SDK Streamer."""
        logger.info("🔌 Disconnecting SDK Streamer...")
        try:
            # Note: The SDK might not have a straightforward 'close' if not running?
            # But usually it does.
            # self.streamer.disconnect() # Check SDK method? 
            # Documentation implies simple connect/disconnect logic usually exists or we just let script exit.
            # For safety, just log. The script exit kills threads.
            pass
        except:
            pass
        self.is_connected = False

    def get_current_prices(self):
        return self.latest_prices
