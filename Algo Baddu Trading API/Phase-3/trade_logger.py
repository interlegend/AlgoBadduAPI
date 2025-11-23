"""
Trade Logger
Logs all signals, trades, and generates reports
"""

import os
import logging
from datetime import datetime
import pandas as pd
import json

logger = logging.getLogger(__name__)

class TradeLogger:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.today = datetime.now().strftime('%Y%m%d')
        
        self.signals_log = []
        self.trades_log = []
        self.events_log = []
        
        # File paths
        self.signals_file = os.path.join(log_dir, f"signals_{self.today}.csv")
        self.trades_file = os.path.join(log_dir, f"trades_{self.today}.csv")
        self.summary_file = os.path.join(log_dir, f"summary_{self.today}.txt")
        self.events_file = os.path.join(log_dir, f"events_{self.today}.json")
    
    def log_signal(self, timestamp, side, nifty_close, ema21, macd_hist, choppiness, option_ltp, strike):
        """Log a trading signal"""
        signal = {
            'timestamp': timestamp,
            'side': side,
            'nifty_close': nifty_close,
            'ema21': ema21,
            'macd_hist': macd_hist,
            'choppiness': choppiness,
            'option_ltp': option_ltp,
            'strike': strike
        }
        
        self.signals_log.append(signal)
        
        logger.info(f"📡 SIGNAL: {side} @ {timestamp.strftime('%H:%M:%S')}")
        logger.info(f"   Strike: {strike} | LTP: ₹{option_ltp} | NIFTY: {nifty_close}")
    
    def log_trade_entry(self, order_details):
        """Log trade entry"""
        logger.info(f"💼 ENTRY: {order_details['side']} {order_details['strike']}")
        logger.info(f"   Order ID: {order_details['order_id']}")
        logger.info(f"   Price: ₹{order_details['entry_price']} | Qty: {order_details['quantity']}")
    
    def log_trade_exit(self, exit_details):
        """Log trade exit"""
        self.trades_log.append(exit_details)
        
        pnl_emoji = "💰" if exit_details['pnl_inr'] > 0 else "❌"
        logger.info(f"{pnl_emoji} EXIT: {exit_details['side']} {exit_details['strike']}")
        logger.info(f"   Order ID: {exit_details['order_id']}")
        logger.info(f"   Exit Price: ₹{exit_details['exit_price']} | Reason: {exit_details['exit_reason']}")
        logger.info(f"   P&L: ₹{exit_details['pnl_inr']:,.2f}")
    
    def log_event(self, event_type, message, data=None):
        """Log a general event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'data': data
        }
        
        self.events_log.append(event)
    
    def save_signals_to_csv(self):
        """Save signals log to CSV"""
        if not self.signals_log:
            return
        
        df = pd.DataFrame(self.signals_log)
        df.to_csv(self.signals_file, index=False)
        logger.info(f"✅ Signals saved to: {self.signals_file}")
    
    def save_trades_to_csv(self):
        """Save trades log to CSV"""
        if not self.trades_log:
            return
        
        df = pd.DataFrame(self.trades_log)
        
        column_order = [
            'order_id', 'signal_time', 'entry_time', 'exit_time',
            'side', 'strike', 'entry_price', 'exit_price', 'quantity',
            'initial_sl', 'sl', 'tp1', 'tp1_hit',
            'exit_reason', 'pnl_points', 'pnl_inr', 'status'
        ]
        
        df = df[[col for col in column_order if col in df.columns]]
        df.to_csv(self.trades_file, index=False)
        logger.info(f"✅ Trades saved to: {self.trades_file}")
    
    def save_events_to_json(self):
        """Save events log to JSON"""
        if not self.events_log:
            return
        
        with open(self.events_file, 'w') as f:
            json.dump(self.events_log, f, indent=2)
        
        logger.info(f"✅ Events saved to: {self.events_file}")
    
    def generate_daily_summary(self, position_tracker):
        """Generate daily summary report"""
        stats = position_tracker.get_daily_stats()
        
        summary = f"""
{'='*70}
TRADER-BADDU LIVE PAPER TRADER - DAILY SUMMARY
{'='*70}
Date: {datetime.now().strftime('%Y-%m-%d')}
Report Generated: {datetime.now().strftime('%H:%M:%S')}

{'='*70}
TRADING STATISTICS
{'='*70}
Total Signals Generated:  {len(self.signals_log)}
Total Trades Executed:    {stats['total_trades']}
Open Positions:           {position_tracker.get_open_position_count()}

Winning Trades:           {stats['winners']}
Losing Trades:            {stats['losers']}
Win Rate:                 {stats['win_rate']:.1f}%

{'='*70}
P&L SUMMARY
{'='*70}
Realized P&L:             ₹{stats['realized_pnl']:,.2f}
Unrealized P&L:           ₹{stats['unrealized_pnl']:,.2f}
Total P&L:                ₹{stats['total_pnl']:,.2f}

{'='*70}
FILES GENERATED
{'='*70}
Signals Log:  {self.signals_file}
Trades Log:   {self.trades_file}
Events Log:   {self.events_file}
Summary:      {self.summary_file}

{'='*70}
"""
        
        # ✅ ADD encoding='utf-8' TO FIX RUPEE SYMBOL ERROR!
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(summary)
        logger.info(f"✅ Summary saved to: {self.summary_file}")
        
        return summary
    
    def save_all(self, position_tracker):
        """Save all logs and generate summary"""
        self.save_signals_to_csv()
        self.save_trades_to_csv()
        self.save_events_to_json()
        self.generate_daily_summary(position_tracker)
        
        logger.info("✅ All logs saved successfully!")