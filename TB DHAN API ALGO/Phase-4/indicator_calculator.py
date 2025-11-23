"""
Real-time Indicator Calculator
Maintains rolling buffer and calculates indicators
"""

import pandas as pd
import numpy as np
from collections import deque
import logging
import pandas_ta as ta  # Using pandas_ta for standardized calculations

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    def __init__(self, buffer_size=500, strategy_params=None):
        self.buffer_size = buffer_size  # Increased buffer size for stability
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
            df['timestamp'] = pd.to_datetime(df['datetime'])
            if 'datetime' in df.columns: df.drop(columns=['datetime'], inplace=True)
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        return df
    
    def EMA(self, series, period):
        """Calculate Exponential Moving Average"""
        # Matches Phase 2: series.ewm(span=period, adjust=False).mean()
        return series.ewm(span=period, adjust=False).mean()
    
    def MACD(self, series, fast=12, slow=26, signal=9):
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = self.EMA(series, fast)
        ema_slow = self.EMA(series, slow)
        macd = ema_fast - ema_slow
        macd_signal = self.EMA(macd, signal)
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def ATR(self, high, low, close, period=7):
        """Calculate Average True Range - Manual implementation matching Phase 2 simple ATR"""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def Vortex(self, high, low, close, period=21):
        """Calculate Vortex Indicator using pandas_ta to match Phase 2"""
        # Phase 2 uses: ta.vortex(high=..., low=..., close=..., length=vi_period)
        # pandas_ta returns a DataFrame with columns VIP_{period} and VIM_{period}
        vortex_df = ta.vortex(high=high, low=low, close=close, length=period)
        
        # Handle cases where vortex_df might be None or empty (not enough data)
        if vortex_df is None or vortex_df.empty:
             return pd.Series([np.nan]*len(close)), pd.Series([np.nan]*len(close))

        # Column names in pandas_ta default to VTXP_{length} and VTXM_{length}
        # or VIP_{length} / VIM_{length} depending on version. 
        # ta.vortex returns 'VTXP_21', 'VTXM_21' usually.
        
        # Let's try to find the columns dynamically
        plus_col = [c for c in vortex_df.columns if c.startswith('VTXP') or c.startswith('VIP')][0]
        minus_col = [c for c in vortex_df.columns if c.startswith('VTXM') or c.startswith('VIM')][0]
        
        return vortex_df[plus_col], vortex_df[minus_col]

    def calculate_nifty_indicators(self):
        """Calculate all required indicators for the NIFTY index using dynamic params"""
        ema_period = self.params.get('ema_period', 21)
        vi_period = self.params.get('vi_period', 21)

        # Ensure we have enough data for EMA warmup (at least period size, ideally more)
        if len(self.nifty_buffer) < max(ema_period, vi_period):
            return False
        
        df = self._buffer_to_df(self.nifty_buffer)
        
        # Calculate indicators
        df[f'ema{ema_period}'] = self.EMA(df['close'], ema_period)
        df['macd'], df['macd_signal'], df['macd_hist'] = self.MACD(df['close'])
        
        # Use the new Vortex function wrapping pandas_ta
        vi_plus, vi_minus = self.Vortex(df['high'], df['low'], df['close'], vi_period)
        df[f'vi_plus_{vi_period}'] = vi_plus
        df[f'vi_minus_{vi_period}'] = vi_minus
        
        self.nifty_df = df
        
        latest = df.iloc[-1]
        
        # Debug logging for specific timestamps (as requested in prompt)
        # 2025-11-20 10:15 is one of the discrepancy points
        debug_ts = pd.Timestamp('2025-11-20 10:15:00')
        if latest['timestamp'] == debug_ts:
             logger.info(f"🕵️ DEBUG {latest['timestamp']}: Close={latest['close']}, EMA={latest[f'ema{ema_period}']:.2f}, VI+={latest[f'vi_plus_{vi_period}']:.4f}, VI-={latest[f'vi_minus_{vi_period}']:.4f}")

        self.nifty_indicators = {
            'close': latest['close'],
            f'ema{ema_period}': latest[f'ema{ema_period}'],
            f'vi_plus_{vi_period}': latest[f'vi_plus_{vi_period}'],
            f'vi_minus_{vi_period}': latest[f'vi_minus_{vi_period}'],
            'macd_hist': latest['macd_hist'],
            'timestamp': latest['timestamp']
        }
        
        return True
    
    def calculate_option_indicators(self, option_type):
        """Calculate all required indicators for CE or PE options"""
        buffer = self.ce_buffer if option_type == 'CE' else self.pe_buffer
        
        if len(buffer) < 10:
            return False
        
        df = self._buffer_to_df(buffer)
        
        # Calculate indicators
        df['atr'] = self.ATR(df['high'], df['low'], df['close'], period=7)
        
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