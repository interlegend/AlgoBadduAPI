import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, ArrowDown, Activity } from 'lucide-react';
import { PriceData } from '../types';

interface PriceCardProps {
  symbol: string;
  data: PriceData;
}

export const PriceCard: React.FC<PriceCardProps> = ({ symbol, data }) => {
  const prevPriceRef = useRef<number>(data.ltp);
  const [flashClass, setFlashClass] = useState('');
  const [direction, setDirection] = useState<'up' | 'down' | 'neutral'>('neutral');

  useEffect(() => {
    if (data.ltp > prevPriceRef.current) {
      setFlashClass('animate-flash-green text-success-green');
      setDirection('up');
    } else if (data.ltp < prevPriceRef.current) {
      setFlashClass('animate-flash-red text-danger-red');
      setDirection('down');
    }

    // Reset animation class after it plays
    const timer = setTimeout(() => {
      setFlashClass('');
    }, 500);

    prevPriceRef.current = data.ltp;

    return () => clearTimeout(timer);
  }, [data.ltp]);

  return (
    <div className="bg-slate-800/40 border-l-4 border-anime-blue rounded-r-lg p-4 transition-all duration-300 transform hover:-translate-y-1 hover:bg-slate-700/40">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider flex items-center gap-2">
          {symbol === 'NIFTY' ? <Activity size={16} /> : null}
          {symbol}
        </h3>
        {direction === 'up' && <ArrowUp size={20} className="text-success-green" />}
        {direction === 'down' && <ArrowDown size={20} className="text-danger-red" />}
      </div>
      
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-mono font-bold ${flashClass || 'text-white'}`}>
          {data.ltp.toFixed(2)}
        </span>
      </div>

      {(data.open || data.high) && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-500 font-mono border-t border-slate-700/50 pt-2">
          <div>
            <span className="block text-[10px] uppercase">Open</span>
            <span className="text-slate-300">{data.open?.toFixed(1) || '-'}</span>
          </div>
          <div>
            <span className="block text-[10px] uppercase">High</span>
            <span className="text-success-green">{data.high?.toFixed(1) || '-'}</span>
          </div>
          <div>
            <span className="block text-[10px] uppercase">Low</span>
            <span className="text-danger-red">{data.low?.toFixed(1) || '-'}</span>
          </div>
        </div>
      )}
    </div>
  );
};