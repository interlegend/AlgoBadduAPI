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
        self.broadcast_queue = asyncio.Queue()

    def trigger_broadcast(self):
        """Thread-safe method to request a UI update."""
        try:
            # This is called from the bot's thread.
            self.broadcast_queue.put_nowait('UPDATE')
        except asyncio.QueueFull:
            pass  # An update is already pending, so we can skip this one.

    async def add_websocket_client(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket_clients.append(websocket)

    def remove_websocket_client(self, websocket: WebSocket):
        self.websocket_clients.remove(websocket)

    async def broadcast_manager(self):
        """A dedicated async task that runs forever on the main event loop."""
        logger.info("Broadcast Manager started.")
        while True:
            try:
                await self.broadcast_queue.get() # Wait for a signal to update
                
                if not self.websocket_clients:
                    continue

                status_data = self.get_status()
                message = json.dumps(status_data, default=str)

                # Create a list of tasks to send messages to all connected clients
                tasks = [client.send_text(message) for client in self.websocket_clients]
                await asyncio.gather(*tasks, return_exceptions=True)

            except Exception as e:
                logger.error(f"Error in broadcast manager: {e}")
                await asyncio.sleep(1)

    def start(self, asset_type: str):
        if self.status == "RUNNING" or self.status == "STARTING":
            logger.warning("Bot is already running or starting.")
            return {"status": "ERROR", "message": "Bot is already running."}

        self.asset_type = asset_type
        self.status = "STARTING"
        self.trigger_broadcast()
        
        self.bot_thread = threading.Thread(target=self._run_bot_logic)
        self.bot_thread.start()
        
        logger.info(f"Trading bot thread initiated for asset: {self.asset_type}")
        return {"status": "SUCCESS", "message": f"Bot is starting for {asset_type}..."}

    def stop(self):
        if self.status != "RUNNING" and self.status != "STARTING":
            logger.warning("Bot is not running.")
            return {"status": "ERROR", "message": "Bot is not running."}

        self.status = "STOPPING"
        self.trigger_broadcast() # Immediately notify UI we are stopping
        
        if self.data_streamer:
            self.data_streamer.disconnect()
        # The _run_bot_logic loop will see the status change and exit gracefully.
        
        logger.info("Bot stop signal sent.")
        return {"status": "SUCCESS", "message": "Bot is stopping."}

    def get_status(self):
        positions = self.position_tracker.get_all_open_positions() if self.position_tracker else []
        prices = self.data_streamer.get_current_prices() if self.data_streamer else {}
        
        ui_prices = prices.copy()
        if self.asset_type and self.asset_type != 'NIFTY' and 'NIFTY' in ui_prices:
            ui_prices[self.asset_type] = ui_prices.pop('NIFTY')
            
        indicators = {}
        if self.indicator_calculator and self.data_streamer:
            nifty_ind = self.indicator_calculator.get_nifty_indicators()
            live_candle = self.data_streamer.current_candles.get('NIFTY')
            if live_candle:
                live_ind = self.indicator_calculator.calculate_live_indicators('NIFTY', live_candle)
                if live_ind:
                    nifty_ind.update(live_ind)

            indicators = {
                'ema': nifty_ind.get('ema21', 0),
                'vi_plus': nifty_ind.get('vi_plus_34', 0),
                'vi_minus': nifty_ind.get('vi_minus_34', 0)
            }

        return {
            "bot_status": self.status,
            "asset": self.asset_type,
            "timestamp": datetime.now().isoformat(),
            "positions": positions,
            "live_prices": ui_prices,
            "indicators": indicators,
            "ui_state": self.ui_state
        }

    def _run_bot_logic(self):
        try:
            logger.info("Initializing bot components in new thread.")
            trade_logger = TradeLogger(os.path.join(PROJECT_ROOT, "trade_logs"))
            self.position_tracker = PositionTracker()
            
            from strategy_v30 import StrategyV30
            strategy = StrategyV30()
            
            if self.asset_type == 'CRUDEOIL': strategy.LOT_SIZE = 100
            elif self.asset_type == 'NATURALGAS': strategy.LOT_SIZE = 1250

            self.indicator_calculator = IndicatorCalculator(buffer_size=500, strategy_params=strategy.get_config())
            signal_scanner = LiveSignalScanner(self.indicator_calculator, self.position_tracker)
            self.order_manager = PaperOrderManager(strategy, self.position_tracker, trade_logger, asset_type=self.asset_type)

            configuration = upstox_client.Configuration()
            configuration.access_token = UPSTOX_ACCESS_TOKEN
            self.api_client = upstox_client.ApiClient(configuration)

            keys = self._get_instrument_keys()
            if not keys.get('nifty'):
                 raise RuntimeError("Failed to get primary instrument key.")

            self.data_streamer = LiveDataStreamer(
                api_client=self.api_client,
                instrument_keys=keys,
                indicator_calculator=self.indicator_calculator,
                on_candle_closed_callback=lambda candle_type: self._signal_handler_callback(signal_scanner, candle_type),
                on_tick_callback=self.trigger_broadcast
            )

            logger.info("Starting data warm-up...")
            self.data_streamer.initialize_warmup(days=10)
            self.indicator_calculator.calculate_nifty_indicators()
            if keys.get('ce'): self.indicator_calculator.calculate_option_indicators('CE')
            if keys.get('pe'): self.indicator_calculator.calculate_option_indicators('PE')
            logger.info("Warm-up complete.")

            logger.info("Starting WebSocket data streamer...")
            self.data_streamer.start_websocket()
            self.status = "RUNNING"
            self.trigger_broadcast()
            
            while self.status == "RUNNING":
                if self.order_manager and self.data_streamer:
                    prices = self.data_streamer.get_current_prices()
                    ce_data = prices.get('CE')
                    pe_data = prices.get('PE')
                    
                    if self.asset_type == 'NIFTY' and ce_data and pe_data:
                         self.order_manager.update_positions(ce_data.get('ltp', 0), pe_data.get('ltp', 0), ce_data.get('high', 0), pe_data.get('high', 0), ce_data, pe_data, self.indicator_calculator.get_nifty_indicators(), datetime.now())
                    elif self.asset_type != 'NIFTY':
                        main_data = prices.get('NIFTY')
                        if main_data:
                             main_ltp = main_data.get('ltp', 0)
                             self.order_manager.update_positions(main_ltp, main_ltp, main_data.get('high', 0), main_data.get('high', 0), main_data, main_data, self.indicator_calculator.get_nifty_indicators(), datetime.now())
                
                time.sleep(0.2) # Loop for SL/TP management, sleeps for 200ms

        except Exception as e:
            logger.error(f"Critical error in bot thread: {e}", exc_info=True)
            self.status = "ERROR"
        finally:
            # Final status update
            self.status = "STOPPED"
            self.trigger_broadcast()
            logger.info("Bot thread has finished execution.")

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
        return keys
        
    def _signal_handler_callback(self, signal_scanner, candle_type):
        if candle_type != 'NIFTY': return
        signal = signal_scanner.on_candle_closed(candle_type)
        self.ui_state["last_signal"] = signal if signal else "WAITING..."
        self.trigger_broadcast()

# ======================================================================================
# FASTAPI APP AND ENDPOINTS
# ======================================================================================
app = FastAPI(
    title="Trader-Baddu API",
    description="The backend powerhouse for the Trader-Baddu live trading dashboard.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

trading_bot = TradingBot()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(trading_bot.broadcast_manager())

@app.post("/start")
async def start_bot_endpoint(asset_type: str = "NIFTY"):
    return trading_bot.start(asset_type)

@app.post("/stop")
async def stop_bot_endpoint():
    return trading_bot.stop()

@app.get("/status")
async def get_bot_status_endpoint():
    return trading_bot.get_status()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await trading_bot.add_websocket_client(websocket)
    try:
        trading_bot.trigger_broadcast()
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
        trading_bot.remove_websocket_client(websocket)

@app.get("/")
async def root():
    return {"status": "ONLINE", "message": "Welcome to the Trader-Baddu API Command Center!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)