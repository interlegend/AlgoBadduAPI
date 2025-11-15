"""
Live Data Streamer - V3 with Protobuf Decoding
Connects to Upstox WebSocket and streams real-time market data
"""

import websocket
import json
import logging
from datetime import datetime, timedelta
import threading
import time
import requests
from protobuf_decoder import UpstoxProtobufDecoder

logger = logging.getLogger(__name__)


class LiveDataStreamer:
    def __init__(self, access_token, instrument_keys, indicator_calculator, on_candle_closed_callback):
        """Initialize Live Data Streamer with Protobuf support"""
        
        self.access_token = access_token
        self.instrument_keys = instrument_keys
        self.indicator_calculator = indicator_calculator
        self.on_candle_closed_callback = on_candle_closed_callback
        
        self.ws = None
        self.is_connected = False
        self.should_reconnect = True
        
        # Protobuf decoder
        self.decoder = UpstoxProtobufDecoder()
        self.decoder.set_instrument_mapping(instrument_keys)
        
        # Current candle data
        self.current_candles = {
            'NIFTY': None,
            'CE': None,
            'PE': None
        }
        
        self.current_candle_start = None
        
        # Latest prices cache
        self.latest_prices = {
            'NIFTY': None,
            'CE': None,
            'PE': None
        }
        
        logger.info("✅ Live Data Streamer initialized (V3 + Protobuf)")
    
    def get_websocket_auth_url(self):
        """Get WebSocket authorization URL from Upstox V3 API"""
        
        try:
            url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            logger.info("🔑 Requesting WebSocket auth URL (V3)...")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    ws_url = data['data']['authorizedRedirectUri']
                    logger.info("✅ WebSocket auth URL received")
                    return ws_url
                else:
                    logger.error(f"❌ API error: {data}")
                    return None
            else:
                logger.error(f"❌ Failed to get auth URL. Status: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Exception: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def connect(self):
        """Connect to Upstox WebSocket V3"""
        
        logger.info("="*70)
        logger.info("📡 CONNECTING TO UPSTOX WEBSOCKET (V3 + PROTOBUF)")
        logger.info("="*70)
        
        ws_auth_url = self.get_websocket_auth_url()
        
        if not ws_auth_url:
            logger.error("❌ Could not get WebSocket auth URL!")
            return False
        
        websocket.enableTrace(False)
        
        self.ws = websocket.WebSocketApp(
            ws_auth_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()
        
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
        """Called when WebSocket opens"""
        logger.info("🔓 WebSocket connection opened!")
        self.is_connected = True
        
        self._subscribe_to_instruments()
    
    def _subscribe_to_instruments(self):
        """Subscribe to instruments"""
        
        instruments = [
            self.instrument_keys['nifty'],
            self.instrument_keys['ce'],
            self.instrument_keys['pe']
        ]
        
        subscribe_message = {
            "guid": "someguid",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": instruments
            }
        }
        
        logger.info("📡 Subscribing to instruments:")
        logger.info(f"   NIFTY: {self.instrument_keys['nifty']}")
        logger.info(f"   CE:    {self.instrument_keys['ce']}")
        logger.info(f"   PE:    {self.instrument_keys['pe']}")
        
        self.ws.send(json.dumps(subscribe_message))
        logger.info("✅ Subscription request sent")
    
    def _on_message(self, ws, message):
        """Called when message received - Decodes protobuf binary data"""
        
        try:
            if isinstance(message, bytes):
                # Decode protobuf
                response = self.decoder.decode_feed_response(message)
                
                if response and 'feeds' in response:
                    for instrument_key, feed_data in response['feeds'].items():
                        self._process_feed_data(feed_data)
                        
            else:
                # JSON message
                try:
                    data = json.loads(message)
                    logger.info(f"📨 JSON Message: {data}")
                except:
                    pass
                
        except Exception as e:
            logger.error(f"💥 Error in _on_message: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_feed_data(self, feed_data):
        """Process decoded feed data"""
        
        instrument_name = feed_data.get('instrument_name', 'UNKNOWN')
        ltp = feed_data.get('ltp')
        
        if ltp is None:
            return
        
        logger.debug(f"📊 {instrument_name}: LTP={ltp:.2f}")
        
        # Get OHLC data if available
        ohlc_data = feed_data.get('ohlc_data', [])
        current_ohlc = None
        
        if ohlc_data:
            for ohlc in ohlc_data:
                if ohlc.get('interval') in ['1m', 'I1', 'I5']:
                    current_ohlc = ohlc
                    break
            if not current_ohlc and ohlc_data:
                current_ohlc = ohlc_data[-1]
        
        # Update latest prices
        if instrument_name in self.latest_prices:
            self.latest_prices[instrument_name] = {
                'ltp': ltp,
                'open': current_ohlc.get('open', ltp) if current_ohlc else ltp,
                'high': current_ohlc.get('high', ltp) if current_ohlc else ltp,
                'low': current_ohlc.get('low', ltp) if current_ohlc else ltp
            }
        
        # Update current candle
        self._update_candle_with_tick(instrument_name, ltp, feed_data, current_ohlc)
    
    def _update_candle_with_tick(self, instrument_name, ltp, feed_data, current_ohlc=None):
        """Update current 5-min candle with tick data"""
        
        now = datetime.now()
        
        if self.current_candle_start is None:
            self.current_candle_start = self._round_to_5min(now)
        
        candle_boundary = self._round_to_5min(now)
        
        if candle_boundary > self.current_candle_start:
            self._close_candles()
            self.current_candle_start = candle_boundary
            self.current_candles = {
                'NIFTY': None,
                'CE': None,
                'PE': None
            }
        
        current = self.current_candles[instrument_name]
        
        if current is None:
            self.current_candles[instrument_name] = {
                'timestamp': self.current_candle_start,
                'open': ltp,
                'high': ltp,
                'low': ltp,
                'close': ltp,
                'volume': feed_data.get('vtt', 0)
            }
        else:
            current['high'] = max(current['high'], ltp)
            current['low'] = min(current['low'], ltp)
            current['close'] = ltp
            current['volume'] = feed_data.get('vtt', current['volume'])
    
    def _round_to_5min(self, dt):
        """Round datetime down to nearest 5-minute boundary"""
        minute = (dt.minute // 5) * 5
        return dt.replace(minute=minute, second=0, microsecond=0)
    
    def _close_candles(self):
        """Close current 5-minute candles"""
        
        logger.info(f"🔔 5-Min Candle Closed @ {self.current_candle_start.strftime('%H:%M')}")
        
        for instrument_type in ['NIFTY', 'CE', 'PE']:
            candle = self.current_candles[instrument_type]
            
            if candle:
                self.indicator_calculator.add_candle(instrument_type, candle)
                logger.debug(f"   {instrument_type}: O={candle['open']:.2f} H={candle['high']:.2f} L={candle['low']:.2f} C={candle['close']:.2f}")
        
        if self.on_candle_closed_callback:
            self.on_candle_closed_callback('NIFTY')
    
    def _on_error(self, ws, error):
        """Called on error"""
        logger.error(f"💥 WebSocket Error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when connection closes"""
        logger.warning(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        
        if self.should_reconnect:
            logger.info("🔄 Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.connect()
    
    def disconnect(self):
        """Disconnect"""
        logger.info("🔌 Disconnecting WebSocket...")
        self.should_reconnect = False
        
        if self.ws:
            self.ws.close()
        
        self.is_connected = False
        logger.info("✅ WebSocket disconnected")
    
    def get_current_prices(self):
        """Get current prices"""
        return self.latest_prices
    
    def is_market_open(self):
        """Check if market is open"""
        now = datetime.now().time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        return market_open <= now <= market_close