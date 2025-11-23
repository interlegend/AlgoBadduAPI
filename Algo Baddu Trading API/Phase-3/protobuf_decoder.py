"""
Upstox Protobuf Decoder - V3 Official
Decodes binary WebSocket messages from Upstox V3 using official proto
"""

import logging
logger = logging.getLogger(__name__)

import upstox_client.feeder.proto.MarketDataFeedV3_pb2 as pb



class UpstoxProtobufDecoder:
    """Decoder for Upstox Market Data Feed V3 protobuf messages"""
    
    def __init__(self):
        self.instrument_map = {}  # Map instrument_key to friendly name
    
    def set_instrument_mapping(self, instrument_keys):
        """
        Set mapping between instrument keys and friendly names
        
        Args:
            instrument_keys: Dict with 'nifty', 'ce', 'pe' instrument keys
        """
        # Map instrument key to friendly name
        self.instrument_map[instrument_keys['nifty']] = 'NIFTY'
        self.instrument_map[instrument_keys['ce']] = 'CE'
        self.instrument_map[instrument_keys['pe']] = 'PE'
        
        logger.info(f"✅ Instrument mapping set: {len(self.instrument_map)} instruments")
    
    def decode_feed_response(self, binary_data):
        """
        Decode Upstox V3 protobuf binary message
        """
        if pb is None:
            return None
        try:
            # Parse protobuf message
            feed_response = pb.FeedResponse()
            feed_response.ParseFromString(binary_data)
            
            # Build response structure
            response = {
                'type': {
                    pb.FeedType_initial_feed: 'initial_feed',
                    pb.FeedType_live_feed: 'live_feed',
                    pb.FeedType_market_info: 'market_info'
                }.get(feed_response.feed_type, 'unknown'),
                'timestamp': feed_response.currentTs,
                'feeds': {}
            }
            
            # Process feeds map
            for instrument_key, feed in feed_response.feeds.items():
                decoded_feed = self._decode_feed(instrument_key, feed)
                if decoded_feed:
                    response['feeds'][instrument_key] = decoded_feed
            
            # Market info (if present)
            if feed_response.HasField('marketInfo'):
                response['market_info'] = self._decode_market_info(feed_response.marketInfo)
            
            return response
            
        except Exception as e:
            logger.error(f"Error decoding protobuf: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _decode_feed(self, instrument_key, feed):
        """Decode individual Feed message"""
        
        data = {
            'instrument_key': instrument_key,
            'instrument_name': self.instrument_map.get(instrument_key, 'UNKNOWN'),
            'request_mode': {
                pb.RequestMode_ltpc: 'ltpc',
                pb.RequestMode_full_d5: 'full_d5',
                pb.RequestMode_option_greeks: 'option_greeks',
                pb.RequestMode_full_d30: 'full_d30'
            }.get(feed.requestMode, 'unknown'),
        }
        
        # Check which feed type we have (oneof FeedUnion)
        feed_type = feed.WhichOneof('FeedUnion')
        
        if feed_type == 'ltpc':
            # LTPC only
            data['feed_type'] = 'ltpc'
            data.update(self._decode_ltpc(feed.ltpc))
            
        elif feed_type == 'fullFeed':
            # Full feed (market or index)
            data['feed_type'] = 'full'
            data.update(self._decode_full_feed(feed.fullFeed))
            
        elif feed_type == 'firstLevelWithGreeks':
            # First level with Greeks
            data['feed_type'] = 'first_level_greeks'
            data.update(self._decode_first_level_greeks(feed.firstLevelWithGreeks))
        
        return data
    
    def _decode_ltpc(self, ltpc):
        """Decode LTPC message"""
        return {
            'ltp': ltpc.ltp,
            'ltt': ltpc.ltt,  # Last traded time
            'ltq': ltpc.ltq,  # Last traded quantity
            'cp': ltpc.cp     # Close price
        }
    
    def _decode_full_feed(self, full_feed):
        """Decode FullFeed message"""
        
        data = {}
        
        # Check oneof FullFeedUnion
        feed_type = full_feed.WhichOneof('FullFeedUnion')
        
        if feed_type == 'marketFF':
            # Market Full Feed (options, futures, stocks)
            data['full_feed_type'] = 'market'
            mff = full_feed.marketFF
            
            # LTPC
            if mff.HasField('ltpc'):
                data.update(self._decode_ltpc(mff.ltpc))
            
            # Market OHLC
            if mff.HasField('marketOHLC'):
                data['ohlc_data'] = self._decode_market_ohlc(mff.marketOHLC)
            
            # Market Level (depth)
            if mff.HasField('marketLevel'):
                data['market_depth'] = self._decode_market_level(mff.marketLevel)
            
            # Option Greeks
            if mff.HasField('optionGreeks'):
                data['greeks'] = self._decode_option_greeks(mff.optionGreeks)
            
            # Additional fields
            data['atp'] = mff.atp  # Average traded price
            data['vtt'] = mff.vtt  # Volume traded today
            data['oi'] = mff.oi    # Open interest
            data['iv'] = mff.iv    # Implied volatility
            data['tbq'] = mff.tbq  # Total buy quantity
            data['tsq'] = mff.tsq  # Total sell quantity
            
        elif feed_type == 'indexFF':
            # Index Full Feed (for indices like NIFTY)
            data['full_feed_type'] = 'index'
            iff = full_feed.indexFF
            
            # LTPC
            if iff.HasField('ltpc'):
                data.update(self._decode_ltpc(iff.ltpc))
            
            # Market OHLC
            if iff.HasField('marketOHLC'):
                data['ohlc_data'] = self._decode_market_ohlc(iff.marketOHLC)
        
        return data
    
    def _decode_first_level_greeks(self, flg):
        """Decode FirstLevelWithGreeks message"""
        
        data = {}
        
        # LTPC
        if flg.HasField('ltpc'):
            data.update(self._decode_ltpc(flg.ltpc))
        
        # First depth
        if flg.HasField('firstDepth'):
            data['first_depth'] = self._decode_quote(flg.firstDepth)
        
        # Option Greeks
        if flg.HasField('optionGreeks'):
            data['greeks'] = self._decode_option_greeks(flg.optionGreeks)
        
        # Additional fields
        data['vtt'] = flg.vtt  # Volume traded today
        data['oi'] = flg.oi    # Open interest
        data['iv'] = flg.iv    # Implied volatility
        
        return data
    
    def _decode_market_ohlc(self, market_ohlc):
        """Decode MarketOHLC (repeated OHLC)"""
        
        ohlc_list = []
        
        for ohlc in market_ohlc.ohlc:
            ohlc_list.append({
                'interval': ohlc.interval,
                'open': ohlc.open,
                'high': ohlc.high,
                'low': ohlc.low,
                'close': ohlc.close,
                'volume': ohlc.vol,
                'timestamp': ohlc.ts
            })
        
        return ohlc_list
    
    def _decode_market_level(self, market_level):
        """Decode MarketLevel (bid/ask quotes)"""
        
        quotes = []
        
        for quote in market_level.bidAskQuote:
            quotes.append(self._decode_quote(quote))
        
        return quotes
    
    def _decode_quote(self, quote):
        """Decode Quote message"""
        return {
            'bid_qty': quote.bidQ,
            'bid_price': quote.bidP,
            'ask_qty': quote.askQ,
            'ask_price': quote.askP
        }
    
    def _decode_option_greeks(self, greeks):
        """Decode OptionGreeks message"""
        return {
            'delta': greeks.delta,
            'theta': greeks.theta,
            'gamma': greeks.gamma,
            'vega': greeks.vega,
            'rho': greeks.rho
        }
    
    def _decode_market_info(self, market_info):
        """Decode MarketInfo message"""
        
        segment_status = {}
        
        for segment, status in market_info.segmentStatus.items():
            segment_status[segment] = pb.MarketStatus.Name(status)
        
        return segment_status