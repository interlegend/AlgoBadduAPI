'''Live Data Streamer - HYBRID V3 (WARM-UP + LIVE)
1. Fetches 5 days of historical data via Upstox Historical API (Warm-Up).
2. Connects to Upstox WebSocket V3 for live ticks.
3. Aggregates 5-minute candles and feeds IndicatorCalculator.
'''

import websocket
import json
import logging
import threading
import time
import requests
from datetime import datetime, timedelta, date
import pandas as pd
import urllib.parse
from protobuf_decoder import UpstoxProtobufDecoder

logger = logging.getLogger(__name__)

# Upstox API Constants
API_HOST = "https://api.upstox.com/v2/"
HISTORICAL_API = "https://api.upstox.com/v2/historical-candle/"

class LiveDataStreamer:
    def __init__(self, access_token, instrument_keys, indicator_calculator, on_candle_closed_callback):
        """
        Initialize Live Data Streamer with Warm-Up capability.
        """
        self.access_token = access_token
        self.instrument_keys = instrument_keys
        self.indicator_calculator = indicator_calculator
        self.on_candle_closed_callback = on_candle_closed_callback
        
        self.ws = None
        self.is_connected = False
        self.running = False
        self.should_reconnect = True
        
        self.decoder = UpstoxProtobufDecoder()
        self.decoder.set_instrument_mapping(instrument_keys)
        
        # Candle management
        self.current_candles = {'NIFTY': None, 'CE': None, 'PE': None}
        self.current_candle_start = None
        self.latest_prices = {'NIFTY': None, 'CE': None, 'PE': None}
        
        logger.info("✅ Live Data Streamer (Hybrid V3) initialized.")

    # ==============================================================================
    #  PART 1: HISTORICAL WARM-UP (THE "TIME MACHINE")
    # ==============================================================================
    
    def initialize_warmup(self, days=5):
        """
        Fetches historical data for NIFTY, CE, and PE to warm up indicators.
        Prevents the '09:30 Ghost Trade' by ensuring EMA/VI are stable.
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
        
        headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}

        for type_label, key in instruments_to_fetch:
            if not key:
                logger.warning(f"⚠️ Skipping Warm-Up for {type_label} (No Key)")
                continue

            encoded_key = urllib.parse.quote(key, safe='')
            url = f"https://api.upstox.com/v3/historical-candle/{encoded_key}/minutes/5/{to_date}/{from_date}"
            
            try:
                # logger.info(f"   Fetching history for {type_label}...")
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
        
        # logger.info(f"   Feeding {len(parsed_candles)} candles to {instrument_type} buffer...")
        
        for candle in parsed_candles:
            self.indicator_calculator.add_candle(instrument_type, candle)
            
        # logger.info(f"✅ {instrument_type} Buffer Ready.")

    # ==============================================================================
    #  PART 2: WEBSOCKET LIVE STREAMING
    # ==============================================================================

    def start_websocket(self):
        """Starts the live WebSocket connection."""
        self.running = True
        logger.info("🚀 Starting WebSocket streamer...")
        return self._connect()

    def _get_websocket_auth_url(self):
        """Get WebSocket authorization URL from Upstox V3 API."""
        try:
            url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
            headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
            # logger.info("🔑 Requesting WebSocket auth URL (V3)...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    ws_url = data['data']['authorizedRedirectUri']
                    # logger.info("✅ WebSocket auth URL received")
                    return ws_url
            logger.error(f"❌ Failed to get auth URL. Status: {response.status_code}, Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"💥 Exception getting auth URL: {e}", exc_info=True)
            return None
    
    def _connect(self):
        """Connect to Upstox WebSocket V3."""
        # logger.info("="*70 + "\n📡 CONNECTING TO UPSTOX WEBSOCKET (V3 + PROTOBUF)\n" + "="*70)
        ws_auth_url = self._get_websocket_auth_url()
        if not ws_auth_url:
            logger.error("❌ Could not get WebSocket auth URL!")
            return False
        
        self.ws = websocket.WebSocketApp(ws_auth_url,
                                         on_open=self._on_open,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)
        
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not self.is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if self.is_connected:
            logger.info("✅ WebSocket connected successfully!")
            return True
        else:
            logger.error("❌ WebSocket connection timeout!")
            return False

    def _on_open(self, ws):
        logger.info("🔓 WebSocket connection opened!")
        self.is_connected = True
        self._subscribe_to_instruments()
    
    def _subscribe_to_instruments(self):
        instruments = [self.instrument_keys['nifty'], self.instrument_keys['ce'], self.instrument_keys['pe']]
        # Filter out None keys just in case
        instruments = [i for i in instruments if i]
        
        # Try LTPC mode first if FULL is failing
        subscribe_message = {"guid": "someguid", "method": "sub", "data": {"mode": "ltpc", "instrumentKeys": instruments}}
        logger.info(f"📡 Subscribing to instruments: {instruments} (Mode: LTPC)")
        self.ws.send(json.dumps(subscribe_message))
        logger.info("✅ Subscription request sent")
    
    def _on_message(self, ws, message):
        try:
            # RAW DEBUG
            # logger.info(f"📥 RAW MSG: Type={type(message)} Len={len(message) if isinstance(message, bytes) else len(str(message))}")
            
            if isinstance(message, bytes):
                response = self.decoder.decode_feed_response(message)
                
                if response and 'feeds' in response:
                    feeds = response['feeds']
                    if feeds:
                        for feed_data in feeds.values():
                            self._process_feed_data(feed_data)
                # Silently ignore empty feeds (like initial market_info)
            else:
                msg_json = json.loads(message)
                logger.info(f"📨 WebSocket Message: {msg_json}")
        except Exception as e:
            logger.error(f"💥 Error in _on_message: {e}", exc_info=True)
    
    def _process_feed_data(self, feed_data):
        instrument_name = feed_data.get('instrument_name', 'UNKNOWN')
        ltp = feed_data.get('ltp')
        
        # DEBUG: Print EVERY tick details to debug missing LTP
        logger.info(f"🔍 TICK RECEIVED: Name={instrument_name} | LTP={ltp} | Mode={feed_data.get('request_mode')} | Keys={list(feed_data.keys())}")
        
        if ltp is None: 
            # Try to find LTP in other fields if structure is different
            # logger.warning(f"⚠️ LTP is None for {instrument_name}. Data: {feed_data}")
            return

        # Try to get OHLC data if available (mode=full)
        ohlc = next((o for o in feed_data.get('ohlc_data', []) if o.get('interval') in ['1m', 'I1', 'I5']), None)
        
        self.latest_prices[instrument_name] = {
            'ltp': ltp, 
            'cp': feed_data.get('cp', ltp), # Capture Close Price
            'open': ohlc.get('open', ltp) if ohlc else ltp, 
            'high': ohlc.get('high', ltp) if ohlc else ltp, 
            'low': ohlc.get('low', ltp) if ohlc else ltp
        }
        self._update_candle_with_tick(instrument_name, ltp, feed_data)

    def _update_candle_with_tick(self, instrument_name, ltp, feed_data):
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
                'volume': feed_data.get('vtt', 0) # Volume Traded Today
            }
        else:
            # Update existing candle
            candle = self.current_candles[instrument_name]
            candle['high'] = max(candle['high'], ltp)
            candle['low'] = min(candle['low'], ltp)
            candle['close'] = ltp
            # Update volume (Upstox sends cumulative volume for day usually, or tick volume? 
            # 'vtt' is Volume Traded Today. For a candle volume we ideally need delta, but for now let's just track current state)
            candle['volume'] = feed_data.get('vtt', candle['volume'])

    def _close_candles(self):
        """Push completed 5-min candles to the Calculator."""
        logger.info(f"🔔 5-Min Candle Closed @ {self.current_candle_start.strftime('%H:%M')}")
        
        # Push NIFTY first
        if self.current_candles['NIFTY']:
            self.indicator_calculator.add_candle('NIFTY', self.current_candles['NIFTY'])
        
        # Then Options
        if self.current_candles['CE']:
            self.indicator_calculator.add_candle('CE', self.current_candles['CE'])
        if self.current_candles['PE']:
            self.indicator_calculator.add_candle('PE', self.current_candles['PE'])
            
        # Trigger callback
        if self.on_candle_closed_callback:
            self.on_candle_closed_callback('NIFTY')
    
    def _on_error(self, ws, error):
        logger.error(f"💥 WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        if self.running and self.should_reconnect:
            logger.info("🔄 Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.start_websocket()

    def disconnect(self):
        """Disconnects the WebSocket."""
        logger.info("🔌 Disconnecting WebSocket...")
        self.running = False
        self.should_reconnect = False
        if self.ws:
            self.ws.close()
        self.is_connected = False
        logger.info("✅ WebSocket disconnected.")

    def get_current_prices(self):
        return self.latest_prices