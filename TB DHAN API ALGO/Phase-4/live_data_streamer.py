"""
Live Data Streamer - V5 (FIXED VERSION)
Implements proper warmup and uses REAL option prices from CSV
TASK B: Dual-Loop Simulation with 60-day warmup
"""
import logging
import threading
import time
from datetime import date
import pandas as pd

from config_live import MOCK_NIFTY_FILE, MOCK_OPTIONS_FILE, MOCK_SPEED_DELAY

logger = logging.getLogger(__name__)

class LiveDataStreamer:
    def __init__(self, access_token, instrument_keys, indicator_calculator, on_candle_closed_callback):
        self.indicator_calculator = indicator_calculator
        self.on_candle_closed_callback = on_candle_closed_callback
        self.running = False
        self.latest_prices = {}
        logger.info("✅ Live Data Streamer initialized for MOCK mode (FIXED VERSION).")

    def start(self):
        self.running = True
        logger.info("🚀 Starting MOCK data streamer with WARMUP...")
        mock_thread = threading.Thread(target=self._run_mock_simulation, daemon=True)
        mock_thread.start()
        return True

    def _run_mock_simulation(self):
        try:
            # === STEP A: LOAD DATA ===
            logger.info(f"📂 Loading NIFTY data from: {MOCK_NIFTY_FILE}")
            nifty_df = pd.read_csv(MOCK_NIFTY_FILE, parse_dates=['datetime'])

            logger.info(f"📂 Loading OPTIONS data from: {MOCK_OPTIONS_FILE}")
            options_df = pd.read_csv(MOCK_OPTIONS_FILE, parse_dates=['datetime'])
            options_df = options_df[options_df['instrument_type'].isin(['CE', 'PE'])]

            # === STEP B: DEFINE REPLAY WINDOW ===
            replay_dates = [date(2025, 11, 18), date(2025, 11, 19), date(2025, 11, 20)]
            logger.info(f"🎯 Replay window: {replay_dates}")

            # === TASK B: FULL CSV WARMUP (Match Phase 2) ===
            # Use ENTIRE CSV history (not 60 days) to match Phase 2's EMA calculation exactly
            warmup_start_date = nifty_df['datetime'].dt.date.min()
            logger.info(f"🔥 WARMUP START: {warmup_start_date} (ENTIRE CSV HISTORY - Matching Phase 2)")
            
            # Filter data for warmup + replay window
            nifty_window_df = nifty_df[
                (nifty_df['datetime'].dt.date >= warmup_start_date) & 
                (nifty_df['datetime'].dt.date <= replay_dates[-1])
            ]
            options_window_df = options_df[
                (options_df['datetime'].dt.date >= warmup_start_date) & 
                (options_df['datetime'].dt.date <= replay_dates[-1])
            ]
            
            # === STEP C: DUAL-LOOP IMPLEMENTATION ===
            warmup_cutoff = replay_dates[0]
            
            # --- LOOP 1: WARMUP (Silent Feed) ---
            logger.info("="*70)
            logger.info("🔄 LOOP 1: WARMUP PHASE (No Callbacks)")
            logger.info("="*70)
            
            nifty_warmup = nifty_window_df[nifty_window_df['datetime'].dt.date < warmup_cutoff]
            logger.info(f"📊 Found {len(nifty_warmup)} NIFTY warmup candles.")
            
            for _, row in nifty_warmup.iterrows():
                candle = row.to_dict()
                if 'datetime' in candle:
                    candle['timestamp'] = candle.pop('datetime')
                self.indicator_calculator.add_candle('NIFTY', candle)
            
            # ✅ CRITICAL: Skip option warmup to match Phase 2's cold start behavior
            # Phase 2 calculates ATR from scratch each day, so first ~14 candles are NaN
            logger.info(f"✅ NIFTY buffer warmed up with {len(nifty_warmup)} candles.")
            logger.info(f"⚠️  OPTION warmup SKIPPED (Cold Start to match Phase 2)")
            
            # Verify warmup success
            buffer_status = self.indicator_calculator.get_buffer_status()
            if buffer_status['nifty'] < 50:
                logger.error(f"❌ FATAL: NIFTY buffer has only {buffer_status['nifty']} candles after warmup!")
                logger.error(f"❌ RISK: 09:30 ghost trade likely! Aborting simulation.")
                self.running = False
                return
            else:
                logger.info(f"✅ STABILITY GATE PASSED: {buffer_status['nifty']} NIFTY candles ready.")

            # === STEP D: LOOP 2: REPLAY (Live Simulation) ===
            logger.info("="*70)
            logger.info("🔄 LOOP 2: LIVE REPLAY PHASE (With Callbacks)")
            logger.info("="*70)
            
            nifty_replay_df = nifty_window_df[
                nifty_window_df['datetime'].dt.date.isin(replay_dates)
            ].set_index('datetime')
            
            options_replay_df = options_window_df.set_index('datetime')

            last_date = None

            for timestamp, nifty_row in nifty_replay_df.iterrows():
                if not self.running:
                    break
                
                # === DAILY RESET LOGIC ===
                current_date = timestamp.date()
                if last_date is not None and current_date > last_date:
                    logger.info(f"🌅 NEW DAY DETECTED: {current_date}. Resetting Option Buffers (Cold Start).")
                    self.indicator_calculator.reset_option_buffers()
                last_date = current_date
                
                # === FETCH SYNCHRONIZED OPTION DATA ===
                try:
                    options_at_t = options_replay_df.loc[timestamp]
                    ce_row = options_at_t[options_at_t['instrument_type'] == 'CE'].iloc[0]
                    pe_row = options_at_t[options_at_t['instrument_type'] == 'PE'].iloc[0]
                except (KeyError, IndexError):
                    # No option data at this timestamp
                    payload = {
                        'timestamp': timestamp,
                        'nifty': nifty_row.to_dict(),
                        'ce': None,
                        'pe': None
                    }
                else:
                    # ✅ REAL OPTION PRICES (not synthetic)
                    payload = {
                        'timestamp': timestamp,
                        'nifty': nifty_row.to_dict(),
                        'ce': ce_row.to_dict(),
                        'pe': pe_row.to_dict()
                    }

                # === UPDATE CACHES AND BUFFERS ===
                self.latest_prices['NIFTY'] = {
                    'ltp': payload['nifty']['close'],
                    **payload['nifty']
                }
                self.indicator_calculator.add_candle('NIFTY', {
                    'timestamp': timestamp,
                    **payload['nifty']
                })
                
                if payload['ce']:
                    self.latest_prices['CE'] = {
                        'ltp': payload['ce']['close'],
                        'strike_price': payload['ce']['strike_price'],
                        **payload['ce']
                    }
                    self.indicator_calculator.add_candle('CE', {
                        'timestamp': timestamp,
                        **payload['ce']
                    })
                
                if payload['pe']:
                    self.latest_prices['PE'] = {
                        'ltp': payload['pe']['close'],
                        'strike_price': payload['pe']['strike_price'],
                        **payload['pe']
                    }
                    self.indicator_calculator.add_candle('PE', {
                        'timestamp': timestamp,
                        **payload['pe']
                    })
                
                # === TRIGGER CALLBACK (Signal Scanner) ===
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