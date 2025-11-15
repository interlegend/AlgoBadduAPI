"""Test official Upstox V3 protobuf"""

import MarketDataFeed_pb2 as pb
from protobuf_decoder import UpstoxProtobufDecoder

# Create test FeedResponse
feed_response = pb.FeedResponse()
feed_response.type = pb.initial_feed
feed_response.currentTs = 1234567890

# Add index feed (NIFTY)
index_feed = feed_response.feeds["NSE_INDEX|Nifty 50"]
index_feed.requestMode = pb.full_d5

# Set index full feed
index_feed.fullFeed.indexFF.ltpc.ltp = 25873.65
index_feed.fullFeed.indexFF.ltpc.ltt = 1234567890
index_feed.fullFeed.indexFF.ltpc.cp = 25850.00

# Add OHLC
ohlc = index_feed.fullFeed.indexFF.marketOHLC.ohlc.add()
ohlc.interval = "I1"
ohlc.open = 25870.00
ohlc.high = 25875.00
ohlc.low = 25865.00
ohlc.close = 25873.65
ohlc.vol = 1000000
ohlc.ts = 1234567890

# Add option feed (CE)
ce_feed = feed_response.feeds["NSE_FO|58970"]
ce_feed.requestMode = pb.full_d5

# Set market full feed
ce_feed.fullFeed.marketFF.ltpc.ltp = 158.30
ce_feed.fullFeed.marketFF.ltpc.cp = 155.00
ce_feed.fullFeed.marketFF.atp = 157.50
ce_feed.fullFeed.marketFF.vtt = 50000
ce_feed.fullFeed.marketFF.oi = 1000000
ce_feed.fullFeed.marketFF.iv = 18.5

# Serialize
binary_data = feed_response.SerializeToString()
print(f"✅ Created protobuf message: {len(binary_data)} bytes")

# Test decoder
decoder = UpstoxProtobufDecoder()
decoder.set_instrument_mapping({
    'nifty': 'NSE_INDEX|Nifty 50',
    'ce': 'NSE_FO|58970',
    'pe': 'NSE_FO|58973'
})

decoded = decoder.decode_feed_response(binary_data)

print(f"\n✅ Decoded response:")
print(f"   Type: {decoded['type']}")
print(f"   Timestamp: {decoded['timestamp']}")
print(f"   Feeds: {len(decoded['feeds'])}")

for key, feed in decoded['feeds'].items():
    print(f"\n   📊 {feed['instrument_name']}:")
    print(f"      LTP: {feed.get('ltp', 'N/A')}")
    if 'ohlc_data' in feed:
        print(f"      OHLC intervals: {len(feed['ohlc_data'])}")