import React from 'react';
import { Position } from '../types';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

interface PositionsTableProps {
  positions: Position[];
}

export const PositionsTable: React.FC<PositionsTableProps> = ({ positions }) => {
  if (positions.length === 0) {
    return (
      <div className="bg-slate-900/60 backdrop-blur-md rounded-lg p-8 text-center border border-slate-800/60 border-dashed shadow-xl">
        <div className="flex justify-center mb-4">
            <span className="text-4xl">🧘‍♂️</span>
        </div>
        <h3 className="text-xl text-slate-300 font-bold mb-2">Zen Mode</h3>
        <p className="text-slate-500">No active positions on the battlefield, bro. Waiting for the signal!</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 backdrop-blur-md rounded-lg overflow-hidden shadow-xl border border-slate-800/60">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-900/80 text-slate-400 text-xs uppercase font-bold tracking-wider">
              <th className="p-4">Symbol</th>
              <th className="p-4">Side</th>
              <th className="p-4 text-right">Entry</th>
              <th className="p-4 text-right">Qty</th>
              <th className="p-4 text-right">PnL</th>
              <th className="p-4 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 font-mono text-sm">
            {positions.map((pos, idx) => {
              const isProfit = pos.pnl >= 0;
              const isCall = pos.symbol.includes('CE') || pos.symbol.includes('FUT'); 
              
              return (
                <tr key={`${pos.symbol}-${idx}`} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-4 font-bold text-white flex items-center gap-2">
                    {pos.symbol}
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold ${isCall ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'}`}>
                      {pos.symbol.includes('PE') ? 'PUT' : 'CALL/FUT'}
                    </span>
                  </td>
                  <td className="p-4 text-right text-slate-300">
                    {pos.entry_price.toFixed(2)}
                  </td>
                  <td className="p-4 text-right text-slate-300">
                    {pos.quantity}
                  </td>
                  <td className={`p-4 text-right font-bold ${isProfit ? 'text-success-green' : 'text-danger-red'}`}>
                    <div className="flex items-center justify-end gap-1">
                        {isProfit ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        {pos.pnl > 0 ? '+' : ''}{pos.pnl.toFixed(2)}
                    </div>
                  </td>
                  <td className="p-4 text-center">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold border ${
                      pos.status === 'OPEN' 
                        ? 'bg-dbz-orange/10 text-dbz-orange border-dbz-orange/30 animate-pulse' 
                        : 'bg-slate-700/20 text-slate-500 border-slate-700'
                    }`}>
                      {pos.status === 'OPEN' && <span className="w-1.5 h-1.5 rounded-full bg-dbz-orange"></span>}
                      {pos.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};