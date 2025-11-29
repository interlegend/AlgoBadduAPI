#TRADER BADDU:D
#PAPERTRADERDYNAMIC.py
import os
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, time
from strategy_v30 import StrategyV30

# ==================== INDICATOR FUNCTIONS ====================
def EMA(series, period):
    """Calculate Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def wilders_smoothing(series, period):
    """
    Calculates Wilder's Smoothing (Relative Moving Average) for a given series.
    Equivalent to an EMA with alpha = 1/period and adjust=False.
    """
    return series.ewm(alpha=1/period, adjust=False).mean()

def calculate_adx(df, period=14):
    """
    Calculates the Average Directional Index (ADX) along with +DI and -DI.

    Args:
        df (pd.DataFrame): DataFrame with 'High', 'Low', and 'Close' columns.
        period (int): The lookback period for ADX calculation (default is 14).

    Returns:
        pd.DataFrame: A DataFrame with 'ADX', '+DI', '-DI' columns.
    """
    df_adx = df.copy()

    # 1. Calculate True Range (TR)
    df_adx['H-L'] = df_adx['High'] - df_adx['Low']
    df_adx['H-PC'] = abs(df_adx['High'] - df_adx['Close'].shift(1))
    df_adx['L-PC'] = abs(df_adx['Low'] - df_adx['Close'].shift(1))
    df_adx['TR'] = df_adx[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 2. Calculate Directional Movement (+DM and -DM)
    df_adx['UpMove'] = df_adx['High'] - df_adx['High'].shift(1)
    df_adx['DownMove'] = df_adx['Low'].shift(1) - df_adx['Low']

    df_adx['+DM'] = 0.0
    df_adx['-DM'] = 0.0

    df_adx.loc[(df_adx['UpMove'] > df_adx['DownMove']) & (df_adx['UpMove'] > 0), '+DM'] = df_adx['UpMove']
    df_adx.loc[(df_adx['DownMove'] > df_adx['UpMove']) & (df_adx['DownMove'] > 0), '-DM'] = df_adx['DownMove']

    # 3. Smooth TR, +DM, and -DM using Wilder's Smoothing
    df_adx['TR_Smooth'] = wilders_smoothing(df_adx['TR'], period)
    df_adx['+DM_Smooth'] = wilders_smoothing(df_adx['+DM'], period)
    df_adx['-DM_Smooth'] = wilders_smoothing(df_adx['-DM'], period)

    df_adx['TR_Smooth'] = df_adx['TR_Smooth'].replace(0, np.nan)

    # 4. Calculate Directional Indicators (+DI and -DI)
    df_adx['+DI'] = (df_adx['+DM_Smooth'] / df_adx['TR_Smooth']) * 100
    df_adx['-DI'] = (df_adx['-DM_Smooth'] / df_adx['TR_Smooth']) * 100

    # 5. Calculate Directional Index (DX)
    df_adx['DI_Sum'] = df_adx['+DI'] + df_adx['-DI']
    df_adx['DI_Sum'] = df_adx['DI_Sum'].replace(0, np.nan)
    df_adx['DX'] = (abs(df_adx['+DI'] - df_adx['-DI']) / df_adx['DI_Sum']) * 100

    # 6. Calculate Average Directional Index (ADX)
    df_adx['ADX'] = wilders_smoothing(df_adx['DX'], period)

    return df_adx[['ADX', '+DI', '-DI']]


def MACD(series, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal, and Histogram"""
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = EMA(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

def calculate_bb_width(close_series, period=20, std_dev=2):
    """Calculate Bollinger Band Width"""
    sma = close_series.rolling(period).mean()
    std = close_series.rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    width = (upper - lower) / sma
    return width

def ATR_simple(high, low, close, period=14):
    """Calculate Average True Range on any OHLC data"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def choppiness_index(df, period=14):
    """Calculate Choppiness Index"""
    high = df['high']
    low = df['low']
    close = df['close']

    # True Range
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

# ==================== TIMESTAMP MATCHING HELPER ====================
def find_next_option_candle(signal_time, option_data_index):
    """
    Find the next available option candle at or after the signal time

    Args:
        signal_time: datetime when signal fired on NIFTY
        option_data_index: DatetimeIndex of option candles
    Returns:
        datetime of next available candle, or None if not found
    """
    # Find candles at or after signal time
    future_candles = option_data_index[option_data_index >= signal_time]
    if len(future_candles) > 0:
        return future_candles[0]  # Return first available
    else:
        return None  # No future candles available

# ==================== DATA LOADING ====================
def load_and_prepare_data(ema_period=13, vi_period=14):
    """Load NIFTY index and ATM options data"""
    print("="*70)
    print("📊 LOADING DATA")
    print("="*70)
    
    # Load NIFTY index data
    print(f"\n[1/2] Loading NIFTY index data...")
    nifty_df = pd.read_csv(r"C:\Users\sakth\Desktop\VSCODE\Algo Baddu Trading API\Phase-2\nifty_5min_last_year.csv")
    nifty_df['datetime'] = pd.to_datetime(nifty_df['datetime'])
    nifty_df['date'] = nifty_df['datetime'].dt.date
    print(f"✅ Loaded {len(nifty_df)} NIFTY candles")
    
    # Rename columns to match strategy expectations
    nifty_df.rename(columns={
        'open': 'index_open',
        'high': 'index_high',
        'low': 'index_low',
        'close': 'index_close'}, inplace=True)
    
    # Calculate indicators on NIFTY (for signals only)
    print(f"\n[INFO] Calculating NIFTY indicators for signal generation (EMA={ema_period}, VI={vi_period})...")
    ema_col = f'ema{ema_period}'
    nifty_df[ema_col] = EMA(nifty_df['index_close'], ema_period)
    nifty_df['macd'], nifty_df['macd_signal'], nifty_df['macd_hist'] = MACD(nifty_df['index_close'])
    
    # ADX on NIFTY
    print(f"\n[INFO] Calculating ADX for trend strength...")
    adx_input_df = pd.DataFrame({
        'High': nifty_df['index_high'],
        'Low': nifty_df['index_low'],
        'Close': nifty_df['index_close']
    })
    adx_output_df = calculate_adx(adx_input_df)
    nifty_df['ADX'] = adx_output_df['ADX']
    nifty_df['+DI'] = adx_output_df['+DI']
    nifty_df['-DI'] = adx_output_df['-DI']

    # BB Width on NIFTY
    print(f"[INFO] Calculating Bollinger Band Width for volatility analysis...")
    nifty_df['bb_width'] = calculate_bb_width(nifty_df['index_close'])

    # Vortex Indicator on NIFTY
    print(f"[INFO] Calculating Vortex Indicator for trend identification...")
    vortex_df = ta.vortex(high=nifty_df['index_high'], low=nifty_df['index_low'], close=nifty_df['index_close'], length=vi_period)
    nifty_df[f'vi_plus_{vi_period}'] = vortex_df[f'VTXP_{vi_period}']
    nifty_df[f'vi_minus_{vi_period}'] = vortex_df[f'VTXM_{vi_period}']

    # Calculate Choppiness Index
    print(f"[INFO] Calculating Choppiness Index...")
    chop_df = pd.DataFrame({
        'high': nifty_df['index_high'],
        'low': nifty_df['index_low'],
        'close': nifty_df['index_close']
    })
    nifty_df['choppiness'] = choppiness_index(chop_df, period=14)
    
    nifty_df.dropna(inplace=True)
    nifty_df.reset_index(drop=True, inplace=True)
    print(f"✅ NIFTY indicators calculated, {len(nifty_df)} valid candles")
    
    # Load ATM options data
    print(f"\n[2/2] Loading ATM options data...")
    # ✅ CORRECT
    options_file_path = r"C:\Users\sakth\Desktop\VSCODE\extras\atm_daily_options_HYBRID_V3_ULTRA_FIXED.csv"
    if not os.path.exists(options_file_path):
        raise FileNotFoundError(f"Options data file not found at: {options_file_path}")
    options_df = pd.read_csv(options_file_path)
    options_df['datetime'] = pd.to_datetime(options_df['datetime'])
    options_df['trading_day'] = pd.to_datetime(options_df['trading_day']).dt.date
    print(f"✅ Loaded {len(options_df)} option candles")
    print(f"   - CE candles: {len(options_df[options_df['instrument_type']=='CE'])}")
    print(f"   - PE candles: {len(options_df[options_df['instrument_type']=='PE'])}")
    print(f"   - Trading days: {options_df['trading_day'].nunique()}")
    
    return nifty_df, options_df

# ==================== BACKTESTING ENGINE ====================
def run_backtest(nifty_df, options_df, ema_period=21, vi_period=21, sl_multiplier=2.0, tp_points=10, trail_atr_multiplier=0.5):
    """
    Run backtest using StrategyV29
    WITH FULLY CONFIGURABLE PARAMETERS
    """
    # 🔥 Initialize strategy with given parameters
    strategy = StrategyV30(
        ema_period=ema_period, 
        vi_period=vi_period,
        sl_multiplier=sl_multiplier,
        tp_points=tp_points,
        trail_atr_multiplier=trail_atr_multiplier
    )
    config = strategy.get_config()
    
    print("\n" + "="*70)
    print(f"🚀 STARTING BACKTEST - V29 (EMA={ema_period}, VI={vi_period}, SL={sl_multiplier}, TP={tp_points}, Trail={trail_atr_multiplier})")
    print("="*70)
    print(f"\n📋 STRATEGY CONFIG:")
    print(f"   Lot Size: {config['lot_size']}")
    print(f"   ATR Period: {config['atr_period']}")
    print(f"   TP1: {config['tp1_points']} pts")
    print(f"   Trail: {config['trail_atr_multiplier']}x ATR | Max SL: {config['max_sl_points']:.1f} pts (₹{config['max_sl_points'] * 75:.0f})")
    
    trades = []
    position = None
    trading_days = sorted(options_df['trading_day'].unique())
    
    print(f"\n[INFO] Processing {len(trading_days)} trading days...")
    print(f"[INFO] ATR Period: {14} candles (faster warmup)\n")
    
    for day_num, current_date in enumerate(trading_days, 1):
        print(f"📅 Day {day_num}/{len(trading_days)}: {current_date}")        
        
        # Get NIFTY data for this day
        day_nifty = nifty_df[nifty_df['date'] == current_date].copy()
        if day_nifty.empty:
            print(f"   ⚠️  No NIFTY data for {current_date}")
            continue        
        
        # Reset index to use iloc properly
        day_nifty = day_nifty.reset_index(drop=True)        
        
        # Get options data for this day
        day_options = options_df[options_df['trading_day'] == current_date].copy()
        if day_options.empty:
            print(f"   ⚠️  No options data for {current_date}")
            continue        
        
        # Separate CE and PE data
        ce_data = day_options[day_options['instrument_type'] == 'CE'].copy()
        pe_data = day_options[day_options['instrument_type'] == 'PE'].copy()        
        
        if ce_data.empty or pe_data.empty:
            print(f"   ⚠️  Missing CE or PE data")
            continue        
        
        # Sort by datetime
        ce_data = ce_data.sort_values('datetime').reset_index(drop=True)
        pe_data = pe_data.sort_values('datetime').reset_index(drop=True)        
        
        # Calculate ATR on OPTION prices
        ce_atr_series = ATR_simple(ce_data['high'], ce_data['low'], ce_data['close'], config['atr_period'])
        pe_atr_series = ATR_simple(pe_data['high'], pe_data['low'], pe_data['close'], config['atr_period'])        
        
        ce_data['option_atr'] = ce_atr_series
        pe_data['option_atr'] = pe_atr_series        
        
        # Set index for fast lookup
        ce_data.set_index('datetime', inplace=True)
        pe_data.set_index('datetime', inplace=True)        
        
        strike = ce_data['strike_price'].iloc[0]
        print(f"   Strike: {strike} | CE: {len(ce_data)} candles | PE: {len(pe_data)} candles")        
        
        day_trades = 0
        day_signals = {"BUY_CE": 0, "BUY_PE": 0}
        matched_entries = 0
        missed_entries = 0        
        
        # Iterate through NIFTY candles for this day
        for idx in range(len(day_nifty)):
            nifty_row = day_nifty.iloc[idx]
            signal_time = nifty_row['datetime']  # Time when signal fires
            current_time_only = signal_time.time()                
            
            # Get NIFTY metrics (for signals and exit logic)
            nifty_close = nifty_row['index_close']
            ema_col = f'ema{ema_period}'
            ema_value = nifty_row[ema_col]
            macd_hist = nifty_row['macd_hist']                
            
            # === ENTRY LOGIC (NEXT CANDLE OPEN) ===
            if not position:
                # 1. Check for signal on the CURRENT NIFTY candle
                signal = strategy.check_entry_signal(day_nifty, idx)
                if signal:
                    day_signals[signal] = day_signals.get(signal, 0) + 1
                    
                    # 2. Plan to execute on the NEXT NIFTY candle
                    next_idx = idx + 1
                    
                    # 3. Boundary Check: Ensure the next candle exists
                    if next_idx < len(day_nifty):
                        execution_time = day_nifty.iloc[next_idx]['datetime']
                        
                        option_data = ce_data if signal == "BUY_CE" else pe_data
                        
                        # 4. Find the corresponding option candle for the execution time
                        exec_option_time = find_next_option_candle(execution_time, option_data.index)
                        
                        if exec_option_time:
                            option_candle = option_data.loc[exec_option_time]
                            option_atr = option_candle['option_atr']

                            # 5. Check for valid data (ATR must be calculated)
                            if pd.notna(option_atr):
                                # 6. Set Entry Price: Open of the execution candle + slippage
                                entry_price = option_candle['open'] + 0.5
                                
                                levels = strategy.calculate_entry_levels(signal, entry_price, option_atr)
                                position = {
                                    'side': signal,
                                    'signal_time': signal_time,         # Time of signal (T)
                                    'entry_time': exec_option_time,     # Time of execution (T+1)
                                    'entry_candle_index': next_idx,     # NIFTY index of execution
                                    'entry_price': entry_price,
                                    'strike': strike,
                                    'sl': levels['sl'],
                                    'initial_sl': levels['sl'],
                                    'tp1': levels['tp1'],
                                    'tp1_hit': False,
                                    'highest': option_candle['high'],
                                    'option_atr': option_atr,
                                }
                                matched_entries += 1
                            else:
                                missed_entries += 1 # Missed due to no ATR
                        else:
                            missed_entries += 1 # Missed due to no option candle
                    else:
                        missed_entries += 1 # Missed because it's the last candle of the day

            # === UNIFIED POSITION MANAGEMENT ===
            if position:
                side = position['side']
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                entry_candle_idx = position['entry_candle_index']

                # ✅ CRITICAL: Skip exit checks on entry candle (prevent same-candle exit)
                if idx == entry_candle_idx:
                    continue  # Must wait for next candle!

                # ... rest of your exit logic continues here

                # === UNIFIED POSITION MANAGEMENT ===
                if position:
                    side = position['side']
                    entry_price = position['entry_price']
                    entry_time = position['entry_time']

                    # Determine the correct option data to use
                    option_data = ce_data if side == "BUY_CE" else pe_data

                    # Find current option candle
                    current_option_time = find_next_option_candle(signal_time, option_data.index)

                    if current_option_time is None or current_option_time < entry_time:
                        continue  # Haven't entered yet or no data

                    current_candle = option_data.loc[current_option_time]
                    option_close = current_candle['close']
                    option_high = current_candle['high']

                    exit_reason = None
                    exit_price = None

                    # --- UNIVERSAL LOGIC FOR BOTH CE AND PE ---

                    # 1. Update highest price reached
                    position['highest'] = max(position.get('highest', option_high), option_high)

                    # 2. Check for TP1 Hit and set profit-lock
                    if not position['tp1_hit'] and strategy.check_tp1_hit(side, option_high, position['tp1']):
                        position['tp1_hit'] = True
                        # Use the new optimized trailing SL of +13 for both!
                        position['sl'] = round(entry_price + 13, 2)
                        print(f"✅ TP1 HIT! {side} SL locked to {position['sl']:.2f}")

                    # 3. Check for Stop Loss Hit
                    if strategy.check_sl_hit(side, option_close, position['sl']):
                        exit_reason = "SL Hit"
                        exit_price = position['sl']

                    # 4. Check for MACD/EMA Reversal Exit (only after TP1)
                    elif strategy.check_macd_ema_exit(side, position['tp1_hit'], nifty_close, ema_value, macd_hist):
                        exit_reason = "MACD/EMA Exit"
                        exit_price = option_close

                    # 5. Check for EOD Exit
                    elif strategy.check_eod_exit(current_time_only):
                        exit_reason = "EOD Exit"
                        exit_price = option_close

                    # --- EXECUTE EXIT ---
                    if exit_reason:
                        pnl_data = strategy.calculate_pnl(side, entry_price, exit_price)
                        slippage_seconds = (entry_time - position['signal_time']).total_seconds()

                        trades.append({
                            'SignalTime': position['signal_time'],
                            'EntryTime': position['entry_time'],
                            'Slippage_Sec': int(slippage_seconds),
                            'Side': side,
                            'Strike': position['strike'],
                            'EntryPrice': entry_price,
                            'ExitTime': current_option_time,
                            'ExitPrice': exit_price,
                            'ExitReason': exit_reason,
                            'SL_Value': position['sl'],
                            'Initial_SL': position['initial_sl'],
                            'TP1_Hit': position['tp1_hit'],
                            'PnL_Points': pnl_data['pnl_points'],
                            'PnL_INR': pnl_data['pnl_inr']
                        })

                        day_trades += 1
                        position = None

        total_signals = day_signals.get('BUY_CE', 0) + day_signals.get('BUY_PE', 0)
        match_rate = (matched_entries / total_signals * 100) if total_signals > 0 else 0
        
        print(f"   🎯 Signals: BUY_CE={day_signals.get('BUY_CE', 0)} | BUY_PE={day_signals.get('BUY_PE', 0)}")
        print(f"   ✅ Matched: {matched_entries} ({match_rate:.1f}%) | ❌ Missed: {missed_entries}")
        print(f"   💼 {day_trades} trades executed\n")
    
    return trades

# ==================== REPORTING ====================
def generate_report(trades):
    """Generate detailed backtest report"""
    print("="*70)
    print("📊 BACKTEST RESULTS - TIMESTAMP MATCHING VERSION")
    print("="*70)
    
    if not trades:
        print("\n❌ No trades executed!")
        return
    
    trade_df = pd.DataFrame(trades)
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = (trade_df['PnL_INR'] > 0).sum()
    losing_trades = (trade_df['PnL_INR'] < 0).sum()
    breakeven_trades = (trade_df['PnL_INR'] == 0).sum()
    winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trade_df['PnL_INR'].sum()
    total_profit = trade_df[trade_df['PnL_INR'] > 0]['PnL_INR'].sum()
    total_loss = abs(trade_df[trade_df['PnL_INR'] < 0]['PnL_INR'].sum())
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
    avg_pnl = trade_df['PnL_INR'].mean()
    max_profit = trade_df['PnL_INR'].max()
    max_loss = trade_df['PnL_INR'].min()
    
    # Slippage analysis
    avg_slippage = trade_df['Slippage_Sec'].mean()
    max_slippage = trade_df['Slippage_Sec'].max()
    
    # Calculate max drawdown
    cumulative_pnl = trade_df['PnL_INR'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max
    max_drawdown = drawdown.min()
    
    # TP1 hit rate
    tp1_hit_count = trade_df['TP1_Hit'].sum()
    tp1_hit_rate = (tp1_hit_count / total_trades * 100) if total_trades > 0 else 0
    
    # Print summary
    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"{'='*70}")
    print(f"Total Trades:        {total_trades}")
    print(f"Winning Trades:      {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
    print(f"Losing Trades:       {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
    print(f"Breakeven Trades:    {breakeven_trades}")
    print(f"\nWinrate:             {winrate:.2f}%")
    print(f"Profit Factor:       {profit_factor:.2f}")
    print(f"TP1 Hit Rate:        {tp1_hit_rate:.1f}% ({tp1_hit_count}/{total_trades})")
    print(f"\n⏱️  EXECUTION SLIPPAGE:")
    print(f"{'='*70}")
    print(f"Avg Slippage:        {avg_slippage:.1f} seconds")
    print(f"Max Slippage:        {max_slippage} seconds")
    print(f"\n💰 P&L BREAKDOWN:")
    print(f"{'='*70}")
    print(f"Total P&L:           ₹{total_pnl:,.2f}")
    print(f"Total Profit:        ₹{total_profit:,.2f}")
    print(f"Total Loss:          ₹{total_loss:,.2f}")
    print(f"Average P&L:         ₹{avg_pnl:,.2f}")
    print(f"Max Profit:          ₹{max_profit:,.2f}")
    print(f"Max Loss:            ₹{max_loss:,.2f}")
    print(f"Max Drawdown:        ₹{max_drawdown:,.2f}")
    
    # Breakdown by side
    print(f"\n📊 BREAKDOWN BY SIDE:")
    print(f"{'='*70}")
    for side in ['BUY_CE', 'BUY_PE']:
        side_trades = trade_df[trade_df['Side'] == side]
        if len(side_trades) > 0:
            side_pnl = side_trades['PnL_INR'].sum()
            side_wins = (side_trades['PnL_INR'] > 0).sum()
            side_winrate = (side_wins / len(side_trades) * 100)
            side_tp1 = side_trades['TP1_Hit'].sum()
            side_avg_slip = side_trades['Slippage_Sec'].mean()
            print(f"{side:12} | Trades: {len(side_trades):3} | WR: {side_winrate:5.1f}% | TP1: {side_tp1:3} | Slip: {side_avg_slip:4.1f}s | P&L: ₹{side_pnl:>10,.2f}")
    
    # Save to CSV
    # ✅ CORRECT - Use hardcoded path
    OUTPUT_DIR = r'C:\Users\sakth\Desktop\VSCODE\Algo Baddu Trading API\Phase-2\trade_logs_verification'
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"V27_Backtest_BUY_ONLY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    trade_df.to_csv(output_file, index=False)
    print(f"\n✅ Trade log saved to: {output_file}")
    
    # Show sample trades
    print(f"\n🔍 SAMPLE TRADES (First 10):")
    print(f"{'='*70}")
    display_cols = ['SignalTime', 'EntryTime', 'Slippage_Sec', 'Side', 'Strike', 'EntryPrice', 'ExitPrice', 'ExitReason', 'PnL_INR']
    print(trade_df[display_cols].head(10).to_string(index=False))
    
    return trade_df

# ==================== MAIN ====================
def main():
    """Main execution function for the final, optimized strategy."""
    print("\n" + "🔥"*35)
    print("   OPERATION TRADER-BADDU: FINAL CHAMPION RUN")
    print("   Strategy V30 (EMA=21, VI=21, SL=2.0, TP=10, Trail=0.5)")
    print("🔥"*35 + "\n")

    # --- Final Winning Parameters ---
    ema_period = 21
    vi_period = 21
    sl_multiplier = 2.0
    tp_points = 10
    trail_atr = 0.5
    
    try:
        # Load data with the winning parameters
        nifty_df, options_df = load_and_prepare_data(ema_period=ema_period, vi_period=vi_period)
        
        # Run backtest with winning parameters
        trades = run_backtest(
            nifty_df, 
            options_df, 
            ema_period=ema_period, 
            vi_period=vi_period,
            sl_multiplier=sl_multiplier,
            tp_points=tp_points,
            trail_atr_multiplier=trail_atr
        )
        
        # Generate and store report
        if trades:
            trade_df = generate_report(trades)
        else:
            print("\n❌ No trades executed for this configuration!")

        print("\n" + "="*70)
        print("✅ MISSION COMPLETE: FINAL STRATEGY VERIFIED!")
        print("="*70 + "\n")
        
        return trade_df

    except Exception as e:
        print(f"\n💥 ERROR during final run: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()