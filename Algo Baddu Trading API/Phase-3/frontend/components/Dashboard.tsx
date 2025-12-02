import React, { useEffect, useState, useCallback } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { Play, Square, Wifi, WifiOff, Terminal, Zap, Crosshair, Clock, Activity } from 'lucide-react';
import { BotData } from '../types';
import { PriceCard } from './PriceCard';
import { PositionsTable } from './PositionsTable';
import { startBot, stopBot } from '../services/apiService';

const WS_URL = 'ws://localhost:8000/ws';

export const Dashboard: React.FC = () => {
  const [botData, setBotData] = useState<BotData | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState('NIFTY'); // STATE ADDED

  // Using react-use-websocket for robust WS handling
  const { lastJsonMessage, readyState } = useWebSocket<BotData>(WS_URL, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
  });

  useEffect(() => {
    if (lastJsonMessage) {
      setBotData(lastJsonMessage);
    }
  }, [lastJsonMessage]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Online',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Offline',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  const isConnected = readyState === ReadyState.OPEN;

  const handleStart = async () => {
    try {
      setErrorMsg(null);
      await startBot(selectedAsset); // FIXED: Passing selected asset
    } catch (e: any) {
      setErrorMsg("Failed to initiate sequence! Check backend.");
    }
  };

  const handleStop = async () => {
    try {
      setErrorMsg(null);
      await stopBot();
      window.location.reload(); // Force a refresh for a clean state
    } catch (e: any) {
      setErrorMsg("Emergency stop failed! Pull the plug!");
    }
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return '--:--:--';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour12: false });
  };

  // Status Badge Logic
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'RUNNING': return 'bg-success-green text-black border-success-green shadow-[0_0_15px_rgba(0,255,157,0.4)]';
      case 'STOPPED': return 'bg-danger-red text-white border-danger-red shadow-[0_0_15px_rgba(255,0,85,0.4)]';
      case 'STARTING': return 'bg-saiyan-gold text-black border-saiyan-gold animate-pulse';
      case 'STOPPING': return 'bg-orange-500 text-white border-orange-500 animate-pulse';
      default: return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const isRunning = botData?.bot_status === 'RUNNING' || botData?.bot_status === 'STARTING';

  return (
    <div className="min-h-screen bg-slate-900 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-800 via-slate-800 to-[#151f32] text-slate-200 font-sans p-4 md:p-8 relative overflow-hidden">
      {/* Background Decor - Intensity Increased */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-anime-blue via-dbz-orange to-danger-red opacity-80"></div>
      
      {/* Subtle grid pattern overlay for that tech feel */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tighter text-white drop-shadow-lg flex items-center gap-3">
              <span className="text-anime-blue">TRADER-BADDU</span> 
              <span className="text-slate-600 text-2xl">CMD_CENTER</span>
            </h1>
            <p className="text-slate-500 font-mono text-sm mt-1 flex items-center gap-2">
              SYSTEM_MODE: <span className="text-dbz-orange font-bold">BRO_MODE_ON 👊</span>
            </p>
          </div>
          
          <div className="flex items-center gap-4">
             {/* Connection Status */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full border ${isConnected ? 'bg-slate-950/50 border-success-green/30 text-success-green' : 'bg-red-950/30 border-red-500/30 text-red-500'}`}>
              {isConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
              <span className="font-mono text-xs font-bold uppercase">{connectionStatus}</span>
            </div>
            
            <div className="bg-slate-950/50 px-4 py-2 rounded-lg border border-slate-700/50 font-mono text-xs text-slate-400 flex items-center gap-2">
              <Clock size={14} />
              {formatTime(botData?.timestamp)}
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {errorMsg && (
          <div className="mb-6 bg-red-500/10 border border-red-500 text-red-400 p-4 rounded-lg flex items-center gap-3">
            <Terminal size={20} />
            <span className="font-mono font-bold">{errorMsg}</span>
          </div>
        )}

        {/* Controls & Main Status */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          
          {/* Bot Status Card - Slightly Brightened */}
          <div className="col-span-2 bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-800/60 shadow-xl flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Zap size={64} />
            </div>
            <div>
              <h2 className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">System Status</h2>
              <div className="flex items-center gap-3 mt-2">
                <span className={`px-4 py-1.5 rounded text-sm font-black uppercase tracking-wider border ${getStatusColor(botData?.bot_status || 'OFFLINE')}`}>
                  {botData?.bot_status || 'UNKNOWN'}
                </span>
                <span className="text-slate-500 text-xs font-mono">{botData?.asset}</span>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* DROPDOWN ADDED */}
              <select 
                value={selectedAsset}
                onChange={(e) => setSelectedAsset(e.target.value)}
                disabled={isRunning}
                className="col-span-1 bg-slate-800 border border-slate-700 rounded-md py-3 px-2 font-bold text-white focus:ring-2 focus:ring-anime-blue disabled:opacity-50"
              >
                <option value="NIFTY">NIFTY</option>
                <option value="CRUDEOIL">CRUDEOIL</option>
                <option value="NATURALGAS">NATURALGAS</option>
              </select>
              <button 
                onClick={handleStart}
                disabled={isRunning}
                className="flex items-center justify-center gap-2 bg-success-green text-slate-900 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold py-3 rounded transition-all hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(0,255,157,0.3)]">
                <Play size={18} fill="currentColor" />
                INITIATE
              </button>
              <button 
                onClick={handleStop}
                disabled={!isRunning}
                className="flex items-center justify-center gap-2 bg-danger-red text-white hover:bg-rose-600 disabled:opacity-50 disabled:cursor-not-allowed font-bold py-3 rounded transition-all hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(255,0,85,0.3)]">
                <Square size={18} fill="currentColor" />
                TERMINATE
              </button>
            </div>
          </div>

          {/* Logic State Cards - Slightly Brightened */}
          <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-800/60 shadow-lg flex flex-col justify-center items-center text-center">
            <div className="mb-2 p-3 bg-slate-800/50 rounded-full text-anime-blue">
              <Crosshair size={24} />
            </div>
            <h3 className="text-slate-400 text-xs uppercase font-bold mb-1">Last Signal</h3>
            <p className="text-2xl font-mono font-bold text-white tracking-wide">
              {botData?.ui_state?.last_signal || 'WAITING...'}
            </p>
          </div>

          <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-800/60 shadow-lg flex flex-col justify-center items-center text-center">
            <div className="mb-2 p-3 bg-slate-800/50 rounded-full text-saiyan-gold">
              <Zap size={24} />
            </div>
            <h3 className="text-slate-400 text-xs uppercase font-bold mb-1">ATM Strike</h3>
            <p className="text-2xl font-mono font-bold text-white tracking-wide">
              {botData?.ui_state?.atm_strike || '---'}
            </p>
          </div>
          
           {/* Indicators Card - NEW & WIDENED */}
           <div className="md:col-span-2 bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-800/60 shadow-lg flex flex-col justify-center items-center text-center relative overflow-hidden">
            <div className="absolute top-0 right-0 p-2 opacity-5">
              <Activity size={48} />
            </div>
            <h3 className="text-slate-400 text-xs uppercase font-bold mb-2 border-b border-slate-700/50 pb-1 w-full">Live Indicators</h3>
            
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm w-full">
              <div className="text-right text-slate-500 font-mono">EMA (21):</div>
              <div className="text-left text-anime-blue font-bold font-mono">
                {botData?.indicators?.ema ? botData.indicators.ema.toFixed(1) : '---'}
              </div>
              
              <div className="text-right text-slate-500 font-mono">VI + / - :</div>
              <div className="text-left font-bold font-mono flex gap-1">
                 <span className="text-success-green">{botData?.indicators?.vi_plus ? botData.indicators.vi_plus.toFixed(3) : '-'}</span>
                 <span className="text-slate-600">/</span>
                 <span className="text-danger-red">{botData?.indicators?.vi_minus ? botData.indicators.vi_minus.toFixed(3) : '-'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Live Prices Grid - Container Brightened */}
        <div className="mb-8">
          <h2 className="text-lg font-bold text-slate-300 mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-anime-blue rounded-sm"></span>
            LIVE MARKET DATA
          </h2>
          
          <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-800/60 shadow-xl">
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {botData?.live_prices && Object.entries(botData.live_prices)
                .filter(([_, data]) => data !== null && data !== undefined) // FILTER NULL DATA
                .map(([symbol, data]) => (
                  <PriceCard key={symbol} symbol={symbol} data={data} />
              ))}
              {(!botData?.live_prices || Object.keys(botData.live_prices).length === 0) && (
                <div className="col-span-3 text-center py-8 text-slate-600 font-mono border border-slate-800 border-dashed rounded-lg">
                  <Activity className="mx-auto mb-2 opacity-50" />
                  Scanning for power levels... (Waiting for Data)
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Positions Section */}
        <div>
          <h2 className="text-lg font-bold text-slate-300 mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-dbz-orange rounded-sm"></span>
            ACTIVE POSITIONS
          </h2>
          <PositionsTable positions={botData?.positions || []} />
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-slate-600 text-xs font-mono">
          <p>TRADER-BADDU V2.0 // POWERED BY GOKU'S WILL AND PYTHON</p>
        </footer>

      </div>
    </div>
  );
};