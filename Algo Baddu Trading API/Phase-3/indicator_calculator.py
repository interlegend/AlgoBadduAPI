"""
Real-time Indicator Calculator
Maintains rolling buffer and calculates indicators
"""

import pandas as pd
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    def __init__(self, buffer_size=100):
        self.buffer_size = buffer_size
        
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
        """Convert a deque buffer to a pandas DataFrame"""
        if not buffer:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(buffer))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def EMA(self, series, period):
        """Calculate Exponential Moving Average"""
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
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def Vortex(self, high, low, close, period=21):
        """Calculate Vortex Indicator (VI+ and VI-)"""
        tr = pd.concat([high - low, np.abs(high - close.shift()), np.abs(low - close.shift())], axis=1).max(axis=1)
        atr_sum = tr.rolling(window=period).sum()

        vm_plus = np.abs(high - low.shift())
        vm_minus = np.abs(low - high.shift())

        vi_plus = vm_plus.rolling(window=period).sum() / atr_sum
        vi_minus = vm_minus.rolling(window=period).sum() / atr_sum

        return vi_plus, vi_minus

    def calculate_nifty_indicators(self):
        """Calculate all required indicators for the NIFTY index"""
        if len(self.nifty_buffer) < 30:
            logger.debug(f"Not enough NIFTY candles to calculate indicators: {len(self.nifty_buffer)}/{30}")
            return False
        
        df = self._buffer_to_df(self.nifty_buffer)
        
        # Calculate indicators
        df['ema21'] = self.EMA(df['close'], 21)
        df['macd'], df['macd_signal'], df['macd_hist'] = self.MACD(df['close'])
        df['vi_plus_21'], df['vi_minus_21'] = self.Vortex(df['high'], df['low'], df['close'], 21)
        
        # Store the full DataFrame
        self.nifty_df = df
        
        # Store latest indicator values for quick access
        latest = df.iloc[-1]
        self.nifty_indicators = {
            'close': latest['close'],
            'ema21': latest['ema21'],
            'vi_plus': latest['vi_plus_21'],
            'vi_minus': latest['vi_minus_21'],
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