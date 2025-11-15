import pandas as pd
import numpy as np

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def ATR(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def MACD(series, fast=12, slow=26, signal=9):
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = EMA(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

def choppiness_index(df, period=14):
    tr = ATR(df, period=1)
    atr_sum = tr.rolling(window=period).sum()
    hh = df['high'].rolling(window=period).max()
    ll = df['low'].rolling(window=period).min()
    ci = 100 * np.log10(atr_sum / (hh - ll)) / np.log10(period)
    return ci
