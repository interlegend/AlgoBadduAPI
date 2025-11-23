'''Live Data Streamer - V3 (LIVE ONLY)
Connects to Upstox WebSocket and streams real-time market data.
This version is for live market data and does not contain any simulation logic.
'''

import websocket
import json
import logging
import threading
import time
import requests
from datetime import datetime
from protobuf_decoder import UpstoxProtobufDecoder

logger = logging.getLogger(__name__)

class LiveDataStreamer:
    def __init__(self, access_token, instrument_keys, indicator_calculator, on_candle_closed_callback):
        """Initialize Live Data Streamer for LIVE trading."""
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
        
        self.current_candles = {'NIFTY': None, 'CE': None, 'PE': None}
        self.current_candle_start = None
        self.latest_prices = {'NIFTY': None, 'CE': None, 'PE': None}
        
        logger.info("✅ Live Data Streamer initialized for LIVE mode.")

    def start(self):
        """Starts the live data streamer by connecting to the WebSocket."""
        self.running = True
        logger.info("🚀 Starting LIVE data streamer...")
        return self._connect()

    def _get_websocket_auth_url(self):
        """Get WebSocket authorization URL from Upstox V3 API."""
        try:
            url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
            headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
            logger.info("🔑 Requesting WebSocket auth URL (V3)...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    ws_url = data['data']['authorizedRedirectUri']
                    logger.info("✅ WebSocket auth URL received")
                    return ws_url
            logger.error(f"❌ Failed to get auth URL. Status: {response.status_code}, Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"💥 Exception getting auth URL: {e}", exc_info=True)
            return None
    
    def _connect(self):
        """Connect to Upstox WebSocket V3."""
        logger.info("="*70 + "\n📡 CONNECTING TO UPSTOX WEBSOCKET (V3 + PROTOBUF)\n" + "="*70)
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
        subscribe_message = {"guid": "someguid", "method": "sub", "data": {"mode": "full", "instrumentKeys": instruments}}
        logger.info(f"📡 Subscribing to instruments: {instruments}")
        self.ws.send(json.dumps(subscribe_message))
        logger.info("✅ Subscription request sent")
    
    def _on_message(self, ws, message):
        try:
            if isinstance(message, bytes):
                response = self.decoder.decode_feed_response(message)
                if response and 'feeds' in response:
                    for feed_data in response['feeds'].values():
                        self._process_feed_data(feed_data)
            else:
                logger.info(f"📨 JSON Message: {json.loads(message)}")
        except Exception as e:
            logger.error(f"💥 Error in _on_message: {e}", exc_info=True)
    
    def _process_feed_data(self, feed_data):
        instrument_name = feed_data.get('instrument_name', 'UNKNOWN')
        ltp = feed_data.get('ltp')
        if ltp is None: return

        ohlc = next((o for o in feed_data.get('ohlc_data', []) if o.get('interval') in ['1m', 'I1', 'I5']), None)
        
        self.latest_prices[instrument_name] = {'ltp': ltp, 'open': ohlc.get('open', ltp) if ohlc else ltp, 'high': ohlc.get('high', ltp) if ohlc else ltp, 'low': ohlc.get('low', ltp) if ohlc else ltp}
        self._update_candle_with_tick(instrument_name, ltp, feed_data)

    def _update_candle_with_tick(self, instrument_name, ltp, feed_data):
        now = datetime.now()
        if self.current_candle_start is None:
            self.current_candle_start = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
        
        if now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0) > self.current_candle_start:
            self._close_candles()
            self.current_candle_start = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
            self.current_candles = {'NIFTY': None, 'CE': None, 'PE': None}

        if self.current_candles[instrument_name] is None:
            self.current_candles[instrument_name] = {'timestamp': self.current_candle_start, 'open': ltp, 'high': ltp, 'low': ltp, 'close': ltp, 'volume': feed_data.get('vtt', 0)}
        else:
            candle = self.current_candles[instrument_name]
            candle['high'] = max(candle['high'], ltp)
            candle['low'] = min(candle['low'], ltp)
            candle['close'] = ltp
            candle['volume'] = feed_data.get('vtt', candle['volume'])

    def _close_candles(self):
        logger.info(f"🔔 5-Min Candle Closed @ {self.current_candle_start.strftime('%H:%M')}")
        for instrument_type, candle in self.current_candles.items():
            if candle:
                self.indicator_calculator.add_candle(instrument_type, candle)
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
            self.start()

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
