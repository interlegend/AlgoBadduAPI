"""
Position Tracker
Manages open positions and calculates real-time P&L
"""

import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PositionTracker:
    def __init__(self):
        self.open_positions = {}  # {order_id: position_dict}
        self.closed_positions = []
        
    def open_position(self, side, strike, entry_price, sl, tp1, entry_time, signal_time):
        """
        Open a new position
        
        Args:
            side: 'BUY_CE' or 'BUY_PE'
            strike: Strike price
            entry_price: Entry price (option premium)
            sl: Stop loss level
            tp1: Take profit 1 level
            entry_time: Actual entry timestamp
            signal_time: When signal was generated
        
        Returns:
            order_id: Unique identifier for this position
        """
        order_id = str(uuid.uuid4())[:8]
        
        position = {
            'order_id': order_id,
            'side': side,
            'strike': strike,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'signal_time': signal_time,
            'quantity': 75,  # LOT_SIZE
            'sl': sl,
            'initial_sl': sl,
            'tp1': tp1,
            'tp1_hit': False,
            'highest_price': entry_price,
            'current_price': entry_price,
            'unrealized_pnl_points': 0.0,
            'unrealized_pnl_inr': 0.0,
            'status': 'OPEN'
        }
        
        self.open_positions[order_id] = position
        
        logger.info(f"✅ Position Opened: {order_id}")
        logger.info(f"   {side} {strike} @ ₹{entry_price} | SL: ₹{sl} | TP1: ₹{tp1}")
        
        return order_id
    
    def update_position(self, order_id, current_price):
        """
        Update position with current price
        
        Args:
            order_id: Position identifier
            current_price: Current option price
        """
        if order_id not in self.open_positions:
            return
        
        position = self.open_positions[order_id]
        position['current_price'] = current_price
        
        # Update highest price (for trailing SL)
        position['highest_price'] = max(position['highest_price'], current_price)
        
        # Calculate unrealized P&L (BUY: profit when price goes up)
        pnl_points = current_price - position['entry_price']
        pnl_inr = pnl_points * position['quantity']
        
        position['unrealized_pnl_points'] = round(pnl_points, 2)
        position['unrealized_pnl_inr'] = round(pnl_inr, 2)
    
    def check_tp1_hit(self, order_id, current_high):
        """
        Check if TP1 has been hit
        
        Args:
            order_id: Position identifier
            current_high: Current candle's high
        
        Returns:
            bool: True if TP1 just hit
        """
        if order_id not in self.open_positions:
            return False
        
        position = self.open_positions[order_id]
        
        if not position['tp1_hit'] and current_high >= position['tp1']:
            position['tp1_hit'] = True
            logger.info(f"🎯 TP1 HIT! Order: {order_id} | {position['side']} {position['strike']}")
            return True
        
        return False
    
    def update_trailing_sl(self, order_id, new_sl):
        """
        Update stop loss to trailing level
        
        Args:
            order_id: Position identifier
            new_sl: New trailing SL level
        """
        if order_id not in self.open_positions:
            return
        
        position = self.open_positions[order_id]
        old_sl = position['sl']
        position['sl'] = new_sl
        
        logger.info(f"🔒 Trailing SL Updated: {order_id}")
        logger.info(f"   {position['side']} {position['strike']} | SL: ₹{old_sl} → ₹{new_sl}")
    
    def close_position(self, order_id, exit_price, exit_reason, exit_time):
        """
        Close a position
        
        Args:
            order_id: Position identifier
            exit_price: Exit price
            exit_reason: Reason for exit
            exit_time: Exit timestamp
        
        Returns:
            dict: Closed position details
        """
        if order_id not in self.open_positions:
            logger.error(f"❌ Cannot close position: {order_id} not found!")
            return None
        
        position = self.open_positions.pop(order_id)
        
        # Calculate final P&L
        pnl_points = exit_price - position['entry_price']
        pnl_inr = pnl_points * position['quantity']
        
        position['exit_price'] = exit_price
        position['exit_reason'] = exit_reason
        position['exit_time'] = exit_time
        position['pnl_points'] = round(pnl_points, 2)
        position['pnl_inr'] = round(pnl_inr, 2)
        position['status'] = 'CLOSED'
        
        self.closed_positions.append(position)
        
        pnl_emoji = "💰" if pnl_inr > 0 else "❌"
        logger.info(f"{pnl_emoji} Position Closed: {order_id}")
        logger.info(f"   {position['side']} {position['strike']} | Exit: ₹{exit_price}")
        logger.info(f"   Reason: {exit_reason} | P&L: ₹{pnl_inr:,.2f}")
        
        return position
    
    def get_position(self, order_id):
        """Get position details"""
        return self.open_positions.get(order_id)
    
    def get_all_open_positions(self):
        """Get all open positions"""
        return list(self.open_positions.values())
    
    def get_open_position_count(self):
        """Get count of open positions"""
        return len(self.open_positions)
    
    def get_total_unrealized_pnl(self):
        """Calculate total unrealized P&L across all positions"""
        total = sum(pos['unrealized_pnl_inr'] for pos in self.open_positions.values())
        return round(total, 2)
    
    def get_daily_realized_pnl(self):
        """Calculate total realized P&L for the day"""
        total = sum(pos['pnl_inr'] for pos in self.closed_positions)
        return round(total, 2)
    
    def get_daily_stats(self):
        """Get daily trading statistics"""
        total_trades = len(self.closed_positions)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'total_pnl': 0.0
            }
        
        winners = sum(1 for pos in self.closed_positions if pos['pnl_inr'] > 0)
        losers = sum(1 for pos in self.closed_positions if pos['pnl_inr'] < 0)
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0.0
        
        realized_pnl = self.get_daily_realized_pnl()
        unrealized_pnl = self.get_total_unrealized_pnl()
        total_pnl = realized_pnl + unrealized_pnl
        
        return {
            'total_trades': total_trades,
            'winners': winners,
            'losers': losers,
            'win_rate': round(win_rate, 1),
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': round(total_pnl, 2)
        }