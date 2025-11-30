"""
Paper Order Manager - FIXED VERSION
Implements T+1 execution: Signal at T, Entry at T+1 (matching Phase 2)
CRITICAL FIX: Added time-check to ensure T+1 execution + same-candle exit protection
"""

import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class PaperOrderManager:
    def __init__(self, strategy, position_tracker, trade_logger):
        """
        Initialize Paper Order Manager
        
        Args:
            strategy: StrategyV30 instance
            position_tracker: PositionTracker instance
            trade_logger: TradeLogger instance
        """
        self.strategy = strategy
        self.position_tracker = position_tracker
        self.trade_logger = trade_logger
        self.config = strategy.get_config()
        
        # === T+1 EXECUTION SYSTEM ===
        # Store pending signal to execute on next candle (matches Phase 2 behavior)
        self.pending_signal = None
        self.pending_signal_time = None
    
    def on_signal_detected(self, signal, signal_time):
        """
        Called when a signal is detected at time T.
        Stores it for execution at T+1 (next candle).
        
        Args:
            signal: 'BUY_CE' or 'BUY_PE'
            signal_time: When signal fired
        """
        # Check if we already have an open position
        if self.position_tracker.get_open_position_count() >= 1:
            logger.debug(f"⚠️ Signal {signal} ignored - position already open")
            return
        
        # Check if we already have a pending signal
        if self.pending_signal:
            logger.debug(f"⚠️ Signal {signal} ignored - pending signal exists")
            return
        
        # Store signal for T+1 execution
        self.pending_signal = signal
        self.pending_signal_time = signal_time
        logger.info(f"📌 SIGNAL QUEUED: {signal} at {signal_time.strftime('%H:%M')} - Will execute at T+1")
    
    def execute_pending_signal(self, ce_data, pe_data, current_time):
        """
        Execute the pending signal at T+1 using OPEN price of current candle.
        This matches Phase 2's behavior: Signal at T, Entry at T+1 open.
        
        CRITICAL FIX: Added check to ensure we're on NEXT candle (T+1), not same candle (T)
        
        Args:
            ce_data: Current CE candle data (dict with 'open', 'close', 'high', 'low', 'atr')
            pe_data: Current PE candle data
            current_time: Current candle timestamp (T+1)
        
        Returns:
            order_id or None
        """
        if not self.pending_signal:
            return None
        
        # 🔥 CRITICAL FIX: Only execute if we're on a FUTURE candle (T+1)
        # This prevents same-candle execution (09:30 signal → 09:30 entry)
        if current_time <= self.pending_signal_time:
            logger.debug(f"⏳ Waiting for T+1... Current: {current_time.strftime('%H:%M')}, Signal: {self.pending_signal_time.strftime('%H:%M')}")
            return None  # Wait for next candle!
        
        signal = self.pending_signal
        signal_time = self.pending_signal_time
        
        # Select correct option data based on signal
        option_data = ce_data if signal == 'BUY_CE' else pe_data
        
        # Validate option data
        if not option_data or pd.isna(option_data.get('open')) or pd.isna(option_data.get('atr')):
            logger.warning(f"❌ Cannot execute {signal}: Missing option data at {current_time.strftime('%H:%M')}")
            self.pending_signal = None
            self.pending_signal_time = None
            return None
        
        # === CRITICAL: USE OPEN PRICE + SLIPPAGE (matches Phase 2) ===
        entry_price = option_data['open'] + 0.5  # 0.5 point slippage
        option_atr = option_data['atr']
        strike = option_data.get('strike_price', 'N/A')
        
        # Calculate entry levels
        levels = self.strategy.calculate_entry_levels(signal, entry_price, option_atr)
        
        # Open position
        order_id = self.position_tracker.open_position(
            side=signal,
            strike=strike,
            entry_price=entry_price,
            sl=levels['sl'],
            tp1=levels['tp1'],
            entry_time=current_time,  # T+1 (execution time)
            signal_time=signal_time   # T (signal time)
        )
        
        # Log trade entry
        position = self.position_tracker.get_position(order_id)
        self.trade_logger.log_trade_entry(position)
        
        # Calculate slippage
        slippage_seconds = (current_time - signal_time).total_seconds()
        logger.info(f"✅ ENTRY EXECUTED: {signal} @ ₹{entry_price:.2f} | SL: {levels['sl']:.2f} | TP1: {levels['tp1']:.2f} | Slippage: {int(slippage_seconds)}s")
        
        # Clear pending signal
        self.pending_signal = None
        self.pending_signal_time = None
        
        return order_id
    
    def update_positions(self, ce_price, pe_price, ce_high, pe_high, ce_data, pe_data, nifty_indicators, current_candle_time):
        """
        Update all open positions with current prices and check for exits.
        
        Args:
            ce_price: Current CE close price
            pe_price: Current PE close price
            ce_high: Current CE high
            pe_high: Current PE high
            ce_data: Full CE candle data (for open price execution)
            pe_data: Full PE candle data
            nifty_indicators: NIFTY indicator values
            current_candle_time: Current candle timestamp
        """
        # === STEP 1: Execute any pending T+1 signal ===
        new_order_id = self.execute_pending_signal(ce_data, pe_data, current_candle_time)
        
        # === STEP 2: Update existing positions ===
        closed_orders = []
        
        for position in self.position_tracker.get_all_open_positions():
            order_id = position['order_id']
            side = position['side']
            entry_time = position['entry_time']
            
            # 🔥 CRITICAL FIX: Skip exit checks on the ENTRY CANDLE
            # This prevents same-candle exit (09:30 entry → 09:30 exit)
            if current_candle_time == entry_time:
                logger.debug(f"⏭️ Skipping exit check for {order_id} (entry candle)")
                continue  # Must wait for next candle!
            
            current_price = ce_price if side == 'BUY_CE' else pe_price
            current_high = ce_high if side == 'BUY_CE' else pe_high
            
            # Update position tracking
            self.position_tracker.update_position(order_id, current_price)
            
            # Check for TP1 hit
            if self.position_tracker.check_tp1_hit(order_id, current_high):
                # ✅ MATCHING PHASE 2: Lock Profit to Entry + 13 points immediately upon TP1
                # This ensures we don't give back profits and exit early to take next trades
                new_sl = round(position['entry_price'] + 13.0, 2)
                self.position_tracker.update_trailing_sl(order_id, new_sl)
                self.trade_logger.log_event('TP1_HIT', f"TP1 hit for {side} {position['strike']}", {'order_id': order_id, 'new_sl': new_sl})
            
            # Check exit conditions
            exit_info = self._check_exit_conditions(position, current_price, nifty_indicators, current_candle_time)
            
            if exit_info:
                exit_reason, exit_price = exit_info
                closed_position = self.position_tracker.close_position(
                    order_id=order_id,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    exit_time=current_candle_time
                )
                if closed_position:
                    self.trade_logger.log_trade_exit(closed_position)
                    closed_orders.append(order_id)
        
        return closed_orders

    def _check_exit_conditions(self, position, current_price, nifty_indicators, current_candle_time):
        """Check all exit conditions for a position"""
        side = position['side']
        
        # Get EMA key dynamically based on strategy config
        ema_period = self.config.get('ema_period', 21)
        ema_key = f'ema{ema_period}'
        
        # 1. Stop Loss
        if self.strategy.check_sl_hit(side, current_price, position['sl']):
            return ("SL Hit", position['sl'])
        
        # 2. MACD/EMA Reversal Exit (only after TP1)
        elif self.strategy.check_macd_ema_exit(
            side=side,
            tp1_hit=position['tp1_hit'],
            nifty_close=nifty_indicators.get('close', 0),
            ema=nifty_indicators.get(ema_key, 0),
            macd_hist=nifty_indicators.get('macd_hist', 0)
        ):
            return ("MACD/EMA Exit", current_price)
        
        # 3. EOD Exit
        elif self.strategy.check_eod_exit(current_candle_time.time()):
            return ("EOD Exit", current_price)
        
        return None
    
    def force_close_all_positions(self, ce_price, pe_price):
        """
        Force close all open positions (EOD)
        
        Args:
            ce_price: Current CE price
            pe_price: Current PE price
        """
        logger.info("🔔 Forcing close of all open positions (EOD)...")
        
        for position in self.position_tracker.get_all_open_positions():
            order_id = position['order_id']
            side = position['side']
            
            exit_price = ce_price if side == 'BUY_CE' else pe_price
            
            closed_position = self.position_tracker.close_position(
                order_id=order_id,
                exit_price=exit_price,
                exit_reason="Force EOD Close",
                exit_time=datetime.now()
            )
            
            if closed_position:
                self.trade_logger.log_trade_exit(closed_position)
        
        logger.info("✅ All positions closed!")
    
    def get_position_summary(self):
        """Get summary of all positions"""
        open_positions = self.position_tracker.get_all_open_positions()
        stats = self.position_tracker.get_daily_stats()
        
        summary = {
            'open_count': len(open_positions),
            'open_positions': open_positions,
            'stats': stats,
            'pending_signal': self.pending_signal
        }
        
        return summary