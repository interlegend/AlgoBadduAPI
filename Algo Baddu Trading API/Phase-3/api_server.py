import asyncio
import logging
import json
import sys
import os
import threading
import time
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# --- Add project root to sys.path for module imports ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'Phase-3'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'UPSTOX-API'))


# --- Core Trading Module Imports ---
from config_live import UPSTOX_ACCESS_TOKEN
from live_data_streamer import LiveDataStreamer
from indicator_calculator import IndicatorCalculator
from live_signal_scanner import LiveSignalScanner
from paper_order_manager import PaperOrderManager
from trade_logger import TradeLogger
from position_tracker import PositionTracker
from atm_selector import ATMSelector
from commodity_selector import CommodityKeySelector
import upstox_client

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (API) %(message)s")
logger = logging.getLogger(__name__)


# ======================================================================================
# TRADING BOT CLASS - THE HEART OF THE SYSTEM
# ======================================================================================
class TradingBot:
    def __init__(self):
        self.bot_thread = None
        self.status = "STOPPED"
        self.api_client = None
        self.data_streamer = None
        self.indicator_calculator = None
        self.order_manager = None
        self.position_tracker = None
        self.asset_type = None
        self.ui_state = {"last_signal": "WAITING...", "atm_strike": "N/A"}
        self.websocket_clients = []

    async def add_websocket_client(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket_clients.append(websocket)

    def remove_websocket_client(self, websocket: WebSocket):
        self.websocket_clients.remove(websocket)

    async def broadcast_status(self):
        # This will be the main method to push data to the UI
        if not self.websocket_clients:
            return

        status_data = self.get_status()
        message = json.dumps(status_data, default=str) # Use default=str for datetime objects

        # Use asyncio.gather to send messages to all clients concurrently
        await asyncio.gather(
            *[client.send_text(message) for client in self.websocket_clients]
        )

    def start(self, asset_type: str):
        if self.status == "RUNNING":
            logger.warning("Bot is already running.")
            return {"status": "ERROR", "message": "Bot is already running."}

        self.asset_type = asset_type
        self.status = "STARTING"
        
        # Run the main bot logic in a separate thread to not block the API
        self.bot_thread = threading.Thread(target=self._run_bot_logic)
        self.bot_thread.start()
        
        logger.info(f"Trading bot thread started for asset: {self.asset_type}")
        return {"status": "SUCCESS", "message": f"Bot is starting for {asset_type}..."}

    def stop(self):
        if self.status != "RUNNING":
            logger.warning("Bot is not running.")
            return {"status": "ERROR", "message": "Bot is not running."}

        self.status = "STOPPING"
        logger.info("Stopping data streamer...")
        if self.data_streamer:
            self.data_streamer.disconnect()
        
        self.status = "STOPPED"
        # Force broadcast status one last time so UI knows we stopped
        asyncio.run(self.broadcast_status())
        
        logger.info("Bot has been stopped.")
        return {"status": "SUCCESS", "message": "Bot stopped."}
    
    def get_status(self):
        # ... (existing code) ...

    def _run_bot_logic(self):
        # ... (existing code) ...
                
                # Broadcast the latest status to all connected websocket clients
                asyncio.run(self.broadcast_status())
                
                time.sleep(0.5) # Broadcast every 0.5 seconds for snappier UI

        except Exception as e:
            logger.error(f"Critical error in bot thread: {e}", exc_info=True)
            self.status = "ERROR"

    def _get_instrument_keys(self):
        keys = {}
        if self.asset_type == "NIFTY":
            logger.info("Detecting NIFTY ATM strikes...")
            selector = ATMSelector(UPSTOX_ACCESS_TOKEN)
            nifty_ltp = selector.get_nifty_spot()
            if nifty_ltp:
                atm_strike, ce_key, pe_key = selector.get_atm_keys(nifty_ltp)
                self.ui_state["atm_strike"] = atm_strike
                keys = {'nifty': "NSE_INDEX|Nifty 50", 'ce': ce_key, 'pe': pe_key}
                logger.info(f"ATM Selected: {atm_strike} | CE: {ce_key} | PE: {pe_key}")
        else:
            logger.info(f"Fetching active future for {self.asset_type}...")
            comm_selector = CommodityKeySelector(UPSTOX_ACCESS_TOKEN)
            fut_key, lot, expiry = comm_selector.get_current_future(self.asset_type)
            if fut_key and lot:
                keys = {'nifty': fut_key, 'ce': None, 'pe': None}
                # The strategy lot size is already set in _run_bot_logic
        return keys
        
    def _signal_handler_callback(self, signal_scanner, candle_type):
        """Callback function passed to the data streamer."""
        if candle_type != 'NIFTY': return

        signal = signal_scanner.on_candle_closed(candle_type)
        self.ui_state["last_signal"] = signal if signal else "WAITING..."
        logger.info(f"Signal Scan Result: {self.ui_state['last_signal']}")
        
        if signal and self.order_manager:
            nifty_data = self.indicator_calculator.get_nifty_indicators()
            signal_time = nifty_data.get('timestamp', datetime.now())
            logger.info(f"Routing signal {signal} to Order Manager.")
            self.order_manager.on_signal_detected(signal, signal_time)


# ======================================================================================
# FASTAPI APP AND ENDPOINTS
# ======================================================================================
app = FastAPI(
    title="Trader-Baddu API",
    description="The backend powerhouse for the Trader-Baddu live trading dashboard.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Global Bot Instance ---
trading_bot = TradingBot()

@app.post("/start")
async def start_bot(asset_type: str = "NIFTY"):
    """Starts the trading bot for the specified asset (NIFTY, CRUDEOIL, NATURALGAS)."""
    return trading_bot.start(asset_type)

@app.post("/stop")
async def stop_bot():
    """Stops the trading bot."""
    return trading_bot.stop()

@app.get("/status")
async def get_bot_status():
    """Gets the current status of the bot, positions, and prices."""
    return trading_bot.get_status()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await trading_bot.add_websocket_client(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
        trading_bot.remove_websocket_client(websocket)

@app.get("/")
async def root():
    return {"status": "ONLINE", "message": "Welcome to the Trader-Baddu API Command Center!"}

if __name__ == "__main__":
    # To run this server: uvicorn api_server:app --reload --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
