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
        
        self.nifty_buffer = deque(maxlen=buffer_size)
        self.ce_buffer = deque(maxlen=buffer_size)
        self.pe_buffer = deque(maxlen=buffer_size)
        
        self.nifty_indicators = {}
        self.ce_indicators = {}
        self.pe_indicators = {}
    
    def add_candle(self, instrument_type, candle):
        """Add new candle to buffer"""
        if instrument_type == 'NIFTY':
            self.nifty_buffer.append(candle)
        elif instrument_type == 'CE':
            self.ce_buffer.append(candle)
        elif instrument_type == 'PE':
            self.pe_buffer.append(candle)
    
    def _buffer_to_df(self, buffer):
        """Convert buffer to pandas DataFrame"""
        if len(buffer) == 0:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(buffer))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def EMA(self, series, period):
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()
    
    def MACD(self, series, fast=12, slow=26, signal=9):
        """Calculate MACD, Signal, and Histogram"""
        ema_fast = self.EMA(series, fast)
        ema_slow = self.EMA(series, slow)
        macd = ema_fast - ema_slow
        macd_signal = self.EMA(macd, signal)
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def ATR(self, high, low, close, period=7):
        """Calculate Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def choppiness_index(self, high, low, close, period=14):
        """Calculate Choppiness Index"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)
        
        atr_sum = tr.rolling(window=period).sum()
        hh = high.rolling(window=period).max()
        ll = low.rolling(window=period).min()
        ci = 100 * np.log10(atr_sum / (hh - ll)) / np.log10(period)
        return ci
    
    def calculate_nifty_indicators(self):
        """Calculate indicators for NIFTY index"""
        if len(self.nifty_buffer) < 30:
            logger.warning(f"⚠️  Not enough NIFTY candles: {len(self.nifty_buffer)}/30")
            return False
        
        df = self._buffer_to_df(self.nifty_buffer)
        
        df['ema21'] = self.EMA(df['close'], 21)
        df['macd'], df['macd_signal'], df['macd_hist'] = self.MACD(df['close'])
        df['choppiness'] = self.choppiness_index(df['high'], df['low'], df['close'])
        
        latest = df.iloc[-1]
        
        self.nifty_indicators = {
            'close': latest['close'],
            'ema21': latest['ema21'],
            'macd': latest['macd'],
            'macd_signal': latest['macd_signal'],
            'macd_hist': latest['macd_hist'],
            'choppiness': latest['choppiness'],
            'timestamp': latest['timestamp']
        }
        
        return True
    
    def calculate_option_indicators(self, option_type):
        """Calculate indicators for CE or PE options"""
        buffer = self.ce_buffer if option_type == 'CE' else self.pe_buffer
        
        if len(buffer) < 10:
            return False
        
        df = self._buffer_to_df(buffer)
        
        df['atr'] = self.ATR(df['high'], df['low'], df['close'], period=7)
        
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
        """Get current NIFTY indicators"""
        return self.nifty_indicators
    
    def get_option_indicators(self, option_type):
        """Get current option indicators"""
        if option_type == 'CE':
            return self.ce_indicators
        else:
            return self.pe_indicators
    
    def get_buffer_status(self):
        """Get status of all buffers"""
        return {
            'nifty': len(self.nifty_buffer),
            'ce': len(self.ce_buffer),
            'pe': len(self.pe_buffer)
        }