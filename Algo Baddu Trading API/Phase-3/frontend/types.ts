import React from 'react';

// YO BRO! This is where we define the shape of our power levels (data).

export interface Position {
  symbol: string;
  entry_price: number;
  quantity: number;
  pnl: number;
  status: 'OPEN' | 'CLOSED';
}

export interface PriceData {
  ltp: number;
  open?: number;
  high?: number;
  low?: number;
}

export interface LivePrices {
  [key: string]: PriceData;
}

export interface UIState {
  last_signal: string;
  atm_strike: string;
}

export interface BotData {
  bot_status: 'RUNNING' | 'STOPPED' | 'STARTING' | 'STOPPING';
  asset: string;
  timestamp: string;
  positions: Position[];
  live_prices: LivePrices;
  ui_state: UIState;
}

// For our internal component props
export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  statusColor?: 'green' | 'red' | 'yellow' | 'blue' | 'gray';
  subValue?: string;
}
