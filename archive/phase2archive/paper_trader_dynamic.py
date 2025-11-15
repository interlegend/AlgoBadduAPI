#TRADER BADDU:D
import os
import pandas as pd
import numpy as np
from datetime import datetime, time
from strategy_v30 import StrategyV30

# ==================== INDICATOR FUNCTIONS ====================

def EMA(series, period):
    """Calculate Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def MACD(series, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal, and Histogram"""
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = EMA(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

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

def bollinger_bands(series, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    middle = series.rolling(window=period).mean()  # Moving Average (middle line)
    std = series.rolling(window=period).std()      # Standard Deviation
    upper = middle + (std * std_dev)               # Upper Band
    lower = middle - (std * std_dev)               # Lower Band
    return upper, middle, lower

# ==================== STRATEGY V25 ENTRY LOGIC ====================


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

def load_and_prepare_data():
    """Load NIFTY index and ATM options data"""
    
    print("="*70)
    print("📊 LOADING DATA")
    print("="*70)
    
    # Load NIFTY index data
    print(f"\n[1/2] Loading NIFTY index data...")
    nifty_df = pd.read_csv(r"C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-2\nifty_5min_last_month.csv")
    nifty_df['datetime'] = pd.to_datetime(nifty_df['datetime'])
    nifty_df['date'] = nifty_df['datetime'].dt.date
    print(f"✅ Loaded {len(nifty_df)} NIFTY candles")
    
    # Rename columns to match strategy expectations
    nifty_df.rename(columns={
        'open': 'index_open',
        'high': 'index_high',
        'low': 'index_low',
        'close': 'index_close'
    }, inplace=True)
    
    # Calculate indicators
    print(f"\n[INFO] Calculating NIFTY indicators for signal generation...")
    nifty_df['ema21'] = EMA(nifty_df['index_close'], 21)
    nifty_df['macd'], nifty_df['macd_signal'], nifty_df['macd_hist'] = MACD(nifty_df['index_close'])

    # ADD BOLLINGER BANDS FOR SCOUT MODE!
    nifty_df['bb_upper'], nifty_df['bb_middle'], nifty_df['bb_lower'] = bollinger_bands(nifty_df['index_close'])

    # Choppiness on NIFTY
    nifty_indicator_df = pd.DataFrame({
        'high': nifty_df['index_high'],
        'low': nifty_df['index_low'],
        'close': nifty_df['index_close']
    })
    nifty_df['choppiness'] = choppiness_index(nifty_indicator_df)
    
    nifty_df.dropna(inplace=True)
    nifty_df.reset_index(drop=True, inplace=True)
    print(f"✅ NIFTY indicators calculated, {len(nifty_df)} valid candles")
    
    # Load ATM options data
    print(f"\n[2/2] Loading ATM options data...")
    options_df = pd.read_csv(r"C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\UPSTOX-API\atm_daily_options_HYBRID_V3.csv")
    options_df['datetime'] = pd.to_datetime(options_df['datetime'])
    options_df['trading_day'] = pd.to_datetime(options_df['trading_day']).dt.date
    print(f"✅ Loaded {len(options_df)} option candles")
    print(f"   - CE candles: {len(options_df[options_df['instrument_type']=='CE'])}")
    print(f"   - PE candles: {len(options_df[options_df['instrument_type']=='PE'])}")
    print(f"   - Trading days: {options_df['trading_day'].nunique()}")
    
    return nifty_df, options_df

# ==================== BACKTESTING ENGINE ====================

def run_backtest(nifty_df, options_df):
    """
    Run backtest using Strategy V30 (THE TITAN SHIFTER!)
    WITH SMART TIMESTAMP MATCHING + ADAPTIVE MODES!
    """

    # 🔥 Initialize V30 strategy
    strategy = StrategyV30()

    print("\n" + "="*70)
    print("🚀 STARTING BACKTEST - V30 TITAN SHIFTER MODE!")
    print("="*70)
    print(f"\n📋 V30 STRATEGY CONFIG:")
    print(f"   Lot Size: {strategy.LOT_SIZE}")
    print(f"   Choppiness Threshold: {strategy.RUMBLING_CHOPPINESS_THRESHOLD}")
    print(f"   Scout Mode - SL: {strategy.SCOUT_SL_MULTIPLIER}x ATR | TP: {strategy.SCOUT_TP1_POINTS} pts")
    print(f"   Rumbling Mode - SL: {strategy.RUMBLING_SL_MULTIPLIER}x ATR | BE: {strategy.RUMBLING_BREAKEVEN_TRIGGER_POINTS} pts")

    trades = []
    position = None

    trading_days = sorted(options_df['trading_day'].unique())

    print(f"\n[INFO] Processing {len(trading_days)} trading days...")
    print(f"[INFO] ATR Period: {strategy.ATR_PERIOD} candles\n")
    
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
        ce_atr_series = ATR_simple(ce_data['high'], ce_data['low'], ce_data['close'], strategy.ATR_PERIOD)
        pe_atr_series = ATR_simple(pe_data['high'], pe_data['low'], pe_data['close'], strategy.ATR_PERIOD)
        
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
            signal_time = nifty_row['datetime']
            current_time_only = signal_time.time()
            
            # === V30 ENTRY LOGIC ===
            if not position:
                # 🔥 USE V30 METHOD - RETURNS DICTIONARY!
                signal_result = strategy.check_entry_signal(day_nifty, idx)
                
                if signal_result:
                    signal = signal_result['signal']  # 'BUY_CE' or 'BUY_PE'
                    mode = signal_result['mode']      # 'scout' or 'rumbling'
                    
                    day_signals[signal] = day_signals.get(signal, 0) + 1
                    print(f"   🎯 {signal} signal in {mode.upper()} mode (Choppiness: {nifty_row['choppiness']:.1f})")

                    if signal == "BUY_CE":
                        # Find next available CE candle at or after signal time
                        next_ce_time = find_next_option_candle(signal_time, ce_data.index)
                        
                        if next_ce_time is not None:
                            ce_candle = ce_data.loc[next_ce_time]
                            option_price = ce_candle['close']
                            option_atr = ce_candle['option_atr']
                            
                            if pd.isna(option_atr):
                                missed_entries += 1
                                continue
                            
                            # 🔥 USE V30 ENTRY LEVELS CALCULATION!
                            levels = strategy.calculate_entry_levels(mode, 'BUY_CE', option_price, option_atr)
                            
                            position = {
                                'side': 'BUY_CE',
                                'mode': mode,  # 🔥 TRACK MODE!
                                'signal_time': signal_time,
                                'entry_time': next_ce_time,
                                'entry_price': option_price,
                                'strike': strike,
                                'sl': levels['sl'],
                                'initial_sl': levels['sl'],
                                'tp1': levels['tp1'],
                                'tp1_hit': False,
                                'shapeshifted': False,  # 🔥 TRACK SHAPESHIFT!
                                'breakeven_activated': False,  # 🔥 TRACK BREAKEVEN!
                                'option_atr': option_atr,  # 🔥 ADD THIS!
                                'highest': ce_candle['high']  # 🔥 ADD THIS!
                            }
                            matched_entries += 1
                        else:
                            missed_entries += 1
                            
                    elif signal == "BUY_PE":
                        next_pe_time = find_next_option_candle(signal_time, pe_data.index)
                        
                        if next_pe_time is not None:
                            pe_candle = pe_data.loc[next_pe_time]
                            option_price = pe_candle['close']
                            option_atr = pe_candle['option_atr']
                            
                            if pd.isna(option_atr):
                                missed_entries += 1
                                continue
                            
                            # 🔥 USE V30 ENTRY LEVELS CALCULATION!
                            levels = strategy.calculate_entry_levels(mode, 'BUY_PE', option_price, option_atr)
                            
                            position = {
                                'side': 'BUY_PE',
                                'mode': mode,  # 🔥 TRACK MODE!
                                'signal_time': signal_time,
                                'entry_time': next_pe_time,
                                'entry_price': option_price,
                                'strike': strike,
                                'sl': levels['sl'],
                                'initial_sl': levels['sl'],
                                'tp1': levels['tp1'],
                                'tp1_hit': False,
                                'shapeshifted': False,  # 🔥 TRACK SHAPESHIFT!
                                'breakeven_activated': False,  # 🔥 TRACK BREAKEVEN!
                                'option_atr': option_atr,  # 🔥 ADD THIS!
                                'highest': pe_candle['high']  # 🔥 ADD THIS!
                            }
                            matched_entries += 1
                        else:
                            missed_entries += 1
            
            # === V30 POSITION MANAGEMENT ===
            if position:
                side = position['side']
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                current_option_time = None
                
                # Get current option candle
                if side == "BUY_CE":
                    current_option_time = find_next_option_candle(signal_time, ce_data.index)
                    if current_option_time is None or current_option_time < entry_time:
                        continue
                    option_candle = ce_data.loc[current_option_time].to_dict()
                    
                elif side == "BUY_PE":
                    current_option_time = find_next_option_candle(signal_time, pe_data.index)
                    if current_option_time is None or current_option_time < entry_time:
                        continue
                    option_candle = pe_data.loc[current_option_time].to_dict()
                
                # 🔥 USE V30 EXIT CONDITIONS!
                exit_reason, exit_price = strategy.check_exit_conditions(position, nifty_row, option_candle)
                
                # Execute exit
                if exit_reason:
                    # Calculate P&L using REAL option price movement
                    pnl_points = exit_price - entry_price  # Same for both CE and PE (BUY ONLY)
                    pnl_inr = pnl_points * strategy.LOT_SIZE
                    
                    # Calculate slippage
                    slippage_seconds = (entry_time - position['signal_time']).total_seconds()
                    
                    trades.append({
                        'SignalTime': position['signal_time'],
                        'EntryTime': position['entry_time'],
                        'Slippage_Sec': int(slippage_seconds),
                        'Side': side,
                        'Mode': position['mode'],  # 🔥 TRACK ORIGINAL MODE!
                        'Shapeshifted': position['shapeshifted'],  # 🔥 TRACK TRANSFORMATION!
                        'Strike': position['strike'],
                        'EntryPrice': entry_price,
                        'ExitTime': current_option_time,
                        'ExitPrice': exit_price,
                        'ExitReason': exit_reason,
                        'SL_Value': position['sl'],
                        'Initial_SL': position['initial_sl'],
                        'TP1_Hit': position.get('tp1_hit', False),
                        'PnL_Points': round(pnl_points, 2),
                        'PnL_INR': round(pnl_inr, 2)
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
        # 🔥 V30 MODE ANALYSIS!
    print(f"\n🦴 V30 MODE ANALYSIS:")
    print(f"{'='*70}")
    for mode in ['scout', 'rumbling']:
        mode_trades = trade_df[trade_df['Mode'] == mode]
        if len(mode_trades) > 0:
            mode_pnl = mode_trades['PnL_INR'].sum()
            mode_wins = (mode_trades['PnL_INR'] > 0).sum()
            mode_winrate = (mode_wins / len(mode_trades) * 100)
            shapeshifted_count = mode_trades['Shapeshifted'].sum()
            print(f"{mode.upper():12} | Trades: {len(mode_trades):3} | WR: {mode_winrate:5.1f}% | Shapeshifted: {shapeshifted_count:3} | P&L: ₹{mode_pnl:>10,.2f}")
    
    total_shapeshifted = trade_df['Shapeshifted'].sum()
    shapeshift_rate = (total_shapeshifted / total_trades * 100) if total_trades > 0 else 0
    print(f"\n🔄 SHAPESHIFT STATS:")
    print(f"Total Shapeshifts: {total_shapeshifted} ({shapeshift_rate:.1f}% of all trades)")
    # Save to CSV
    OUTPUT_DIR = r'C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-2\trade_logs_verification'
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"V30_Backtest_TITAN_SHIFTER_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    trade_df.to_csv(output_file, index=False)
    
    print(f"\n✅ Trade log saved to: {output_file}")
    
    # Show sample trades
    print(f"\n🔍 SAMPLE TRADES (First 10):")
    print(f"{'='*70}")
    display_cols = ['SignalTime', 'EntryTime', 'Slippage_Sec', 'Side', 'Mode', 'Shapeshifted', 'Strike', 'EntryPrice', 'ExitPrice', 'ExitReason', 'PnL_INR']
    print(trade_df[display_cols].head(10).to_string(index=False))
    
    return trade_df

# ==================== MAIN ====================

def main():
    """Main execution function"""
    
    print("\n" + "🔥"*35)
    print("   OPERATION TRADER-BADDU: BUY ONLY PAPER TRADER")
    print("   Timestamp Matching + Strategy V30 TITAN SHIFTER!")
    print("   King Claude Edition - Complete")
    print("🔥"*35 + "\n")
    
    try:
        # Load data
        nifty_df, options_df = load_and_prepare_data()
        
        # Run backtest
        trades = run_backtest(nifty_df, options_df)
        
        # Generate report
        trade_df = generate_report(trades)
        
        print("\n" + "="*70)
        print("✅ BACKTEST COMPLETED SUCCESSFULLY!")
        print("="*70 + "\n")
        
        return trade_df
        
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()