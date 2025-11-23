"""
Live Data Streamer - V4 (True Data Matrix Replay)
This version is for MOCK simulation only.
"""
import logging
import threading
import time
from datetime import date
import pandas as pd

from config_live import MOCK_NIFTY_FILE, MOCK_OPTIONS_FILE, MOCK_SPEED_DELAY, MOCK_DAYS_TO_REPLAY, INCLUDE_TODAY

logger = logging.getLogger(__name__)

class LiveDataStreamer:
    def __init__(self, access_token, instrument_keys, indicator_calculator, on_candle_closed_callback):
        self.indicator_calculator = indicator_calculator
        self.on_candle_closed_callback = on_candle_closed_callback
        self.running = False
        self.latest_prices = {}
        logger.info("✅ Live Data Streamer initialized for MOCK mode (True Data Matrix Replay).")

    def start(self):
        self.running = True
        logger.info("🚀 Starting MOCK data streamer...")
        mock_thread = threading.Thread(target=self._run_mock_simulation, daemon=True)
        mock_thread.start()
        return True

    def _run_mock_simulation(self):
        try:
            # Step A: Load and Preprocess Data
            logger.info(f"Loading NIFTY data from: {MOCK_NIFTY_FILE}")
            nifty_df = pd.read_csv(MOCK_NIFTY_FILE, parse_dates=['datetime'])

            logger.info(f"Loading OPTIONS data from: {MOCK_OPTIONS_FILE}")
            options_df = pd.read_csv(MOCK_OPTIONS_FILE, parse_dates=['datetime'])
            options_df = options_df[options_df['instrument_type'].isin(['CE', 'PE'])]

            # Step B: Date Selection for Replay and Warm-up
            replay_dates = [date(2025, 11, 18), date(2025, 11, 19), date(2025, 11, 20)]
            logger.info(f"Replay window set for: {replay_dates}")

            # Define a wider window for warm-up data (e.g., 10 calendar days before start)
            warmup_start_date = replay_dates[0] - pd.Timedelta(days=10)
            
            # Filter for the entire window (warm-up + replay)
            nifty_window_df = nifty_df[(nifty_df['datetime'].dt.date >= warmup_start_date) & (nifty_df['datetime'].dt.date <= replay_dates[-1])]
            options_window_df = options_df[(options_df['datetime'].dt.date >= warmup_start_date) & (options_df['datetime'].dt.date <= replay_dates[-1])]
            
            # Pre-fill indicator calculator with warm-up data
            logger.info("Pre-filling indicators with warm-up data...")
            warmup_cutoff = replay_dates[0]
            
            # NIFTY Warmup
            nifty_warmup = nifty_window_df[nifty_window_df['datetime'].dt.date < warmup_cutoff]
            for _, row in nifty_warmup.iterrows():
                candle = row.to_dict()
                if 'datetime' in candle:
                    candle['timestamp'] = candle.pop('datetime')
                self.indicator_calculator.add_candle('NIFTY', candle)
            
            # OPTION Warmup
            options_warmup = options_window_df[options_window_df['datetime'].dt.date < warmup_cutoff]
            for _, row in options_warmup.iterrows():
                 inst_type = row.get('instrument_type') # 'CE' or 'PE'
                 if inst_type in ['CE', 'PE']:
                    candle = row.to_dict()
                    if 'datetime' in candle:
                        candle['timestamp'] = candle.pop('datetime')
                    self.indicator_calculator.add_candle(inst_type, candle)

            logger.info(f"Indicators warmed up with {len(nifty_warmup)} NIFTY and {len(options_warmup)} Option candles.")

            # Step C: The Replay Loop (only on the target 3 days)
            nifty_replay_df = nifty_window_df[nifty_window_df['datetime'].dt.date.isin(replay_dates)].set_index('datetime')
            options_replay_df = options_window_df.set_index('datetime')

            for timestamp, nifty_row in nifty_replay_df.iterrows():
                if not self.running: break
                
                try:
                    options_at_t = options_replay_df.loc[timestamp]
                    ce_row = options_at_t[options_at_t['instrument_type'] == 'CE'].iloc[0]
                    pe_row = options_at_t[options_at_t['instrument_type'] == 'PE'].iloc[0]
                except (KeyError, IndexError):
                    payload = {'timestamp': timestamp, 'nifty': nifty_row.to_dict(), 'ce': None, 'pe': None}
                else:
                    payload = {'timestamp': timestamp, 'nifty': nifty_row.to_dict(), 'ce': ce_row.to_dict(), 'pe': pe_row.to_dict()}

                # Update caches and indicators for the current candle
                self.latest_prices['NIFTY'] = {'ltp': payload['nifty']['close'], **payload['nifty']}
                self.indicator_calculator.add_candle('NIFTY', {'timestamp': timestamp, **payload['nifty']})
                if payload['ce']:
                    self.latest_prices['CE'] = {'ltp': payload['ce']['close'], **payload['ce']}
                    self.indicator_calculator.add_candle('CE', {'timestamp': timestamp, **payload['ce']})
                if payload['pe']:
                    self.latest_prices['PE'] = {'ltp': payload['pe']['close'], **payload['pe']}
                    self.indicator_calculator.add_candle('PE', {'timestamp': timestamp, **payload['pe']})
                
                self.on_candle_closed_callback('NIFTY')
                time.sleep(MOCK_SPEED_DELAY)
            
            logger.info("✅ Mock simulation finished.")
            self.running = False
        except Exception as e:
            logger.error(f"💥 FATAL ERROR in mock simulation: {e}", exc_info=True)
            self.running = False

    def disconnect(self):
        logger.info("🔌 Disconnecting streamer...")
        self.running = False
        logger.info("✅ Streamer disconnected.")

    def get_current_prices(self):
        return self.latest_prices
