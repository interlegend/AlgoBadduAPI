"""
Real-time Indicator Calculator - FIXED VERSION
Maintains rolling buffer and calculates indicators with STRICT stability gates
"""

import pandas as pd
import numpy as np
from collections import deque
import logging
import pandas_ta as ta

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    def __init__(self, buffer_size=5000, strategy_params=None):
        self.buffer_size = buffer_size
        self.params = strategy_params if strategy_params else {}
        
        # Data buffers
        self.nifty_buffer = deque(maxlen=buffer_size)
        self.ce_buffer = deque(maxlen=buffer_size)
        self.pe_buffer = deque(maxlen=buffer_size)
        
        # DataFrames with indicators
        self.nifty_df = pd.DataFrame()
        self.ce_df = pd.DataFrame()
        self.pe_df = pd.DataFrame()
        
        # Latest indicator values
        self.nifty_indicators = {}
        self.ce_indicators = {}
        self.pe_indicators = {}
    
    def add_candle(self, instrument_type, candle):
        """Add new candle to the appropriate buffer"""
        if instrument_type == 'NIFTY':
            self.nifty_buffer.append(candle)
        elif instrument_type == 'CE':
            self.ce_buffer.append(candle)
        elif instrument_type == 'PE':
            self.pe_buffer.append(candle)
    
    def _buffer_to_df(self, buffer):
        """Convert a deque buffer to a pandas DataFrame and standardize timestamp column."""
        if not buffer:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(buffer))
        
        # Standardize the timestamp column to 'timestamp'
        if 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'], utc=True)
            if 'datetime' in df.columns: 
                df.drop(columns=['datetime'], inplace=True)
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
        # Force TZ-naive to prevent mixing errors downstream
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].dt.tz_convert(None)
            
        return df
    
    def EMA(self, series, period):
        """Calculate Exponential Moving Average - matches Phase 2"""
        return series.ewm(span=period, adjust=False).mean()
    
    def MACD(self, series, fast=12, slow=26, signal=9):
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = self.EMA(series, fast)
        ema_slow = self.EMA(series, slow)
        macd = ema_fast - ema_slow
        macd_signal = self.EMA(macd, signal)
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def ATR(self, high, low, close, period=14):
        """Calculate Average True Range - simple rolling mean matching Phase 2"""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _calculate_true_range(self, high, low, close):
        """Helper to calculate True Range Series"""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr

    def Vortex(self, high, low, close, period=21):
        """
        Calculate Vortex Indicator MANUALLY to match TradingView/Groww EXACTLY.
        Formula:
        VI+ = Sum(Abs(High - Low[1]), n) / Sum(TR, n)
        VI- = Sum(Abs(Low - High[1]), n) / Sum(TR, n)
        """
        tr = self._calculate_true_range(high, low, close)
        
        # Vortex Movements
        vm_plus = np.abs(high - low.shift(1))
        vm_minus = np.abs(low - high.shift(1))
        
        # Sum over period
        sum_tr = tr.rolling(period).sum()
        sum_vm_plus = vm_plus.rolling(period).sum()
        sum_vm_minus = vm_minus.rolling(period).sum()
        
        # Calculate VI
        vi_plus = sum_vm_plus / sum_tr
        vi_minus = sum_vm_minus / sum_tr
        
        return vi_plus, vi_minus

    def Choppiness(self, high, low, close, period=14):
        """
        Calculate Choppiness Index MANUALLY to match TradingView/Groww EXACTLY.
        Formula: 100 * LOG10( SUM(TR, n) / ( MaxHi(n) - MinLo(n) ) ) / LOG10(n)
        """
        tr = self._calculate_true_range(high, low, close)
        sum_tr = tr.rolling(period).sum()
        
        max_hi = high.rolling(period).max()
        min_lo = low.rolling(period).min()
        
        # Avoid division by zero
        range_diff = max_hi - min_lo
        range_diff = range_diff.replace(0, np.nan) 
        
        # Calculate Chop
        # 100 * Log10(SumTR / Range) / Log10(n)
        x = sum_tr / range_diff
        chop = 100 * np.log10(x) / np.log10(period)
        
        return chop

    def calculate_nifty_indicators(self):
        """
        Calculate all required indicators for the NIFTY index.
        CRITICAL STABILITY GATE: Requires minimum 50 candles to prevent cold-start hallucinations.
        """
        # === TASK A: STRICT STABILITY GATE ===
        # This prevents the 09:30 Ghost Trade by blocking unstable indicator calculations
        if len(self.nifty_buffer) < 50:
            logger.debug(f"⏳ Stability Gate: Only {len(self.nifty_buffer)}/50 candles. Indicators blocked.")
            return False

        ema_period = self.params.get('ema_period', 21)
        vi_period = self.params.get('vi_period', 21)

        # Additional safety: ensure we have enough data for the indicators
        if len(self.nifty_buffer) < max(ema_period, vi_period):
            logger.debug(f"⏳ Insufficient data for EMA({ema_period})/VI({vi_period})")
            return False
        
        # === DAILY CANDLE COUNT GATE ===
        # Block signals until we have at least 13 candles of the current trading day
        # This prevents 09:15-10:00 false signals that Phase 2 doesn't generate
        # 13 candles = 10:15 AM (matching Phase 2's first signal time on Nov 19/20)
        df_temp = self._buffer_to_df(self.nifty_buffer)
        if not df_temp.empty:
            latest_date = df_temp.iloc[-1]['timestamp'].date()
            today_candles = df_temp[df_temp['timestamp'].dt.date == latest_date]
            if len(today_candles) < 13:
                logger.info(f"⏳ Daily Candle Gate: Only {len(today_candles)}/13 candles today. Blocking early signals.")
                return False
        
        df = self._buffer_to_df(self.nifty_buffer)
        
        # Calculate indicators
        df[f'ema{ema_period}'] = self.EMA(df['close'], ema_period)
        df['macd'], df['macd_signal'], df['macd_hist'] = self.MACD(df['close'])
        
        # Vortex (Manual)
        vi_plus, vi_minus = self.Vortex(df['high'], df['low'], df['close'], vi_period)
        df[f'vi_plus_{vi_period}'] = vi_plus
        df[f'vi_minus_{vi_period}'] = vi_minus

        # Choppiness Index (Manual)
        chop_period = self.params.get('chop_period', 14)
        df[f'CHOP_{chop_period}'] = self.Choppiness(df['high'], df['low'], df['close'], chop_period)
        
        self.nifty_df = df
        
        latest = df.iloc[-1]
        
        self.nifty_indicators = {
            'close': latest['close'],
            f'ema{ema_period}': latest[f'ema{ema_period}'],
            f'vi_plus_{vi_period}': latest[f'vi_plus_{vi_period}'],
            f'vi_minus_{vi_period}': latest[f'vi_minus_{vi_period}'],
            'macd_hist': latest['macd_hist'],
            f'CHOP_{chop_period}': latest.get(f'CHOP_{chop_period}', 0), # Safely get chop value
            'timestamp': latest['timestamp']
        }
        
        # 🔍 DEBUG: Log 09:30 indicator values to compare with Phase 2
        if latest['timestamp'].time().hour == 9 and latest['timestamp'].time().minute == 30:
            logger.warning(f"🔍 09:30 DEBUG | Date: {latest['timestamp'].date()}")
            logger.warning(f"   Buffer Size: {len(self.nifty_buffer)} candles")
            logger.warning(f"   Close: {latest['close']:.2f} | EMA: {latest[f'ema{ema_period}']:.2f}")
            logger.warning(f"   VI+: {latest[f'vi_plus_{vi_period}']:.4f} | VI-: {latest[f'vi_minus_{vi_period}']:.4f}")
            
            # Check previous candle for crossover detection
            if len(df) >= 2:
                prev = df.iloc[-2]
                prev_gap = prev[f'vi_plus_{vi_period}'] - prev[f'vi_minus_{vi_period}']
                curr_gap = latest[f'vi_plus_{vi_period}'] - latest[f'vi_minus_{vi_period}']
                logger.warning(f"   Prev Gap: {prev_gap:.4f} | Curr Gap: {curr_gap:.4f} | Widening: {curr_gap > prev_gap}")
        
        return True
    
    def calculate_option_indicators(self, option_type):
        """Calculate all required indicators for CE or PE options"""
        buffer = self.ce_buffer if option_type == 'CE' else self.pe_buffer
        
        atr_period = self.params.get('atr_period', 14)
        
        # Ensure enough data for ATR calculation
        if len(buffer) < atr_period:
            return False
        
        df = self._buffer_to_df(buffer)
        
        # Calculate ATR
        df['atr'] = self.ATR(df['high'], df['low'], df['close'], period=atr_period)
        
        # Store the full DataFrame
        if option_type == 'CE':
            self.ce_df = df
        else:
            self.pe_df = df
        
        # Store latest indicator values
        latest = df.iloc[-1]
        indicators = {
            'close': latest['close'],
            'high': latest['high'],
            'low': latest['low'],
            'open': latest['open'],
            'atr': latest['atr'],
            'timestamp': latest['timestamp']
        }
        
        if option_type == 'CE':
            self.ce_indicators = indicators
        else:
            self.pe_indicators = indicators
        
        return True
    
    def get_nifty_indicators(self):
        """Get the latest NIFTY indicators as a dictionary"""
        return self.nifty_indicators
        
    def get_nifty_data(self):
        """Get the entire NIFTY DataFrame"""
        return self.nifty_df

    def get_option_indicators(self, option_type):
        """Get the latest option indicators as a dictionary"""
        return self.ce_indicators if option_type == 'CE' else self.pe_indicators

    def get_option_data(self, option_type):
        """Get the entire option DataFrame"""
        return self.ce_df if option_type == 'CE' else self.pe_df

    def get_buffer_status(self):
        """Get the current size of all data buffers"""
        return {
            'nifty': len(self.nifty_buffer),
            'ce': len(self.ce_buffer),
            'pe': len(self.pe_buffer)
        }

    def reset_option_buffers(self):
        """Reset option buffers for daily cold start simulation (matches Phase 2)"""
        self.ce_buffer.clear()
        self.pe_buffer.clear()
        self.ce_df = pd.DataFrame()
        self.pe_df = pd.DataFrame()
        self.ce_indicators = {}
        self.pe_indicators = {}
        logger.info("🧹 Option buffers cleared for new day (Cold Start).")

    def calculate_live_indicators(self, instrument_type, live_candle):
        """
        Calculate indicators for a forming candle (Real-Time).
        Does NOT update the permanent buffer. Returns snapshot dict.
        """
        if instrument_type != 'NIFTY':
            return {}

        # Quick check for buffer size
        if len(self.nifty_buffer) < 50:
            return {}

        # Create temp buffer: history + live_candle
        temp_data = list(self.nifty_buffer)
        temp_data.append(live_candle)
        
        df = pd.DataFrame(temp_data)
        
        # Standardize timestamp and fix TZ mismatch
        # Use utc=True to handle mixed aware/naive inputs safely
        if 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'], utc=True)
            df.drop(columns=['datetime'], inplace=True)
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
        # Convert back to naive to match strategy logic (if needed)
        df['timestamp'] = df['timestamp'].dt.tz_convert(None)

        ema_period = self.params.get('ema_period', 21)
        vi_period = self.params.get('vi_period', 21)
        
        # 1. Calculate EMA
        # We only strictly need the last value, but pandas ewm is vectorized.
        ema_series = self.EMA(df['close'], ema_period)
        
        # 2. Calculate Vortex (Manual)
        vi_plus_series, vi_minus_series = self.Vortex(df['high'], df['low'], df['close'], vi_period)
        
        # 3. Calculate Choppiness (Manual)
        chop_period = self.params.get('chop_period', 14)
        chop_series = self.Choppiness(df['high'], df['low'], df['close'], chop_period)

        # Get latest values
        latest_idx = -1
        latest_ema = ema_series.iloc[latest_idx]
        latest_vi_plus = vi_plus_series.iloc[latest_idx]
        latest_vi_minus = vi_minus_series.iloc[latest_idx]
        latest_chop = chop_series.iloc[latest_idx]
        
        return {
            f'ema{ema_period}': latest_ema,
            f'vi_plus_{vi_period}': latest_vi_plus,
            f'vi_minus_{vi_period}': latest_vi_minus,
            f'CHOP_{chop_period}': latest_chop,
            'timestamp': df.iloc[latest_idx]['timestamp']
        }