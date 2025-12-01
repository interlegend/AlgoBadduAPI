import upstox_client
import inspect
import pkgutil

print(f"Upstox Client Location: {upstox_client.__file__}")

# Helper to recursively search for the class
def find_class(module, class_name):
    for name, obj in inspect.getmembers(module):
        if name == class_name:
            return f"{module.__name__}.{name}"
        if inspect.ismodule(obj) and obj.__name__.startswith('upstox_client'):
            # Avoid infinite recursion/loops if possible, though pkgutil helps
            pass

print("Searching for MarketDataStreamerV3...")

# Try common locations
try:
    from upstox_client.feeder.market_data_feed import MarketDataFeed
    print("Found MarketDataFeed in upstox_client.feeder.market_data_feed")
except ImportError:
    pass

try:
    import upstox_client.feeder
    print(f"Feeder content: {dir(upstox_client.feeder)}")
except ImportError:
    print("No feeder module")

# Check for the specific file requested
try:
    from upstox_client import market_data_streamer_v3
    print("Found upstox_client.market_data_streamer_v3")
except ImportError as e:
    print(f"Could not import upstox_client.market_data_streamer_v3: {e}")
