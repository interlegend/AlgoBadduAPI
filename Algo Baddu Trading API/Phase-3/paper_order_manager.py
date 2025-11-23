"""
Paper Order Manager
Manages simulated orders and position lifecycle
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaperOrderManager:
    def __init__(self, strategy, position_tracker, trade_logger):
        """
        Initialize Paper Order Manager
        
        Args:
            strategy: StrategyV27 instance
            position_tracker: PositionTracker instance
            trade_logger: TradeLogger instance
        """
        self.strategy = strategy
        self.position_tracker = position_tracker
        self.trade_logger = trade_logger
        self.config = strategy.get_config()
    
    def create_paper_order(self, signal, option_price, option_atr, strike, signal_time):
        """
        Create a paper order based on signal
        
        Args:
            signal: 'BUY_CE' or 'BUY_PE'
            option_price: Current option LTP
            option_atr: Option's ATR value
            strike: Strike price
            signal_time: When signal was generated
        
        Returns:
            order_id or None if order not created
        """
        
        # Check max positions
        if self.position_tracker.get_open_position_count() >= 3:
            logger.warning(f"⚠️  Max positions reached! Signal ignored: {signal}")
            return None
        
        # Calculate entry levels using strategy
        levels = self.strategy.calculate_entry_levels(signal, option_price, option_atr)
        
        entry_time = datetime.now()
        
        # Open position
        order_id = self.position_tracker.open_position(
            side=signal,
            strike=strike,
            entry_price=option_price,
            sl=levels['sl'],
            tp1=levels['tp1'],
            entry_time=entry_time,
            signal_time=signal_time
        )
        
        # Log trade entry
        position = self.position_tracker.get_position(order_id)
        self.trade_logger.log_trade_entry(position)
        
        return order_id
    
    def update_positions(self, ce_price, pe_price, ce_high, pe_high, nifty_indicators):
        """
        Update all open positions with current prices
        
        Args:
            ce_price: Current CE close price
            pe_price: Current PE close price
            ce_high: Current CE high
            pe_high: Current PE high
            nifty_indicators: Dict with NIFTY indicator values
        
        Returns:
            list: Order IDs that were closed
        """
        closed_orders = []
        
        for position in self.position_tracker.get_all_open_positions():
            order_id = position['order_id']
            side = position['side']
            
            # Get current price for this side
            if side == 'BUY_CE':
                current_price = ce_price
                current_high = ce_high
            elif side == 'BUY_PE':
                current_price = pe_price
                current_high = pe_high
            else:
                continue
            
            # Update position with current price
            self.position_tracker.update_position(order_id, current_price)
            
            # Check TP1
            if self.position_tracker.check_tp1_hit(order_id, current_high):
                # Calculate trailing SL
                new_sl = self.strategy.calculate_trailing_sl(side, position['entry_price'])
                self.position_tracker.update_trailing_sl(order_id, new_sl)
                
                self.trade_logger.log_event(
                    'TP1_HIT',
                    f"TP1 hit for {side} {position['strike']}",
                    {'order_id': order_id, 'new_sl': new_sl}
                )
            
            # Check exit conditions
            exit_info = self._check_exit_conditions(position, current_price, nifty_indicators)
            
            if exit_info:
                exit_reason, exit_price = exit_info
                
                # Close position
                closed_position = self.position_tracker.close_position(
                    order_id=order_id,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    exit_time=datetime.now()
                )
                
                if closed_position:
                    self.trade_logger.log_trade_exit(closed_position)
                    closed_orders.append(order_id)
        
        return closed_orders
    
    def _check_exit_conditions(self, position, current_price, nifty_indicators):
        """
        Check all exit conditions for a position
        
        Args:
            position: Position dict
            current_price: Current option price
            nifty_indicators: NIFTY indicator values
        
        Returns:
            tuple: (exit_reason, exit_price) or None
        """
        side = position['side']
        
        # Check SL Hit
        if self.strategy.check_sl_hit(side, current_price, position['sl']):
            return ("SL Hit", position['sl'])
        
        # Check MACD/EMA Exit (only after TP1)
        if self.strategy.check_macd_ema_exit(
            side=side,
            tp1_hit=position['tp1_hit'],
            nifty_close=nifty_indicators.get('close', 0),
            ema21=nifty_indicators.get('ema21', 0),
            macd_hist=nifty_indicators.get('macd_hist', 0)
        ):
            return ("MACD/EMA Exit", current_price)
        
        # Check EOD Exit
        current_time = datetime.now().time()
        if self.strategy.check_eod_exit(current_time):
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
            'stats': stats
        }
        
        return summary