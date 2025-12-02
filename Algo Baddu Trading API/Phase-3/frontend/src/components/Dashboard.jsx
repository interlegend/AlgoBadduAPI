import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';

const API_BASE_URL = "http://localhost:8000";
const WS_BASE_URL = "ws://localhost:8000/ws";

const Dashboard = () => {
    const [botData, setBotData] = useState(null);
    const [selectedAsset, setSelectedAsset] = useState("NIFTY");
    const [isConnected, setIsConnected] = useState(false);
    const socketRef = useRef(null);

    useEffect(() => {
        // Function to connect to the WebSocket
        const connect = () => {
            console.log("Attempting to connect WebSocket...");
            const socket = new WebSocket(WS_BASE_URL);
            socketRef.current = socket;

            socket.onopen = () => {
                console.log("WebSocket Connected!");
                setIsConnected(true);
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setBotData(data);
                } catch (error) {
                    console.error("Failed to parse WebSocket message:", error);
                }
            };

            socket.onclose = () => {
                console.log("WebSocket Disconnected. Attempting to reconnect in 3 seconds...");
                setIsConnected(false);
                setTimeout(connect, 3000); // Attempt to reconnect after 3 seconds
            };

            socket.onerror = (error) => {
                console.error("WebSocket Error:", error);
                socket.close(); // This will trigger the onclose event and reconnection logic
            };
        };

        connect();

        // Cleanup on component unmount
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
        };
    }, []);

    const handleStart = async () => {
        console.log(`Sending START command for asset: ${selectedAsset}`);
        try {
            const response = await fetch(`${API_BASE_URL}/start?asset_type=${selectedAsset}`, {
                method: 'POST',
            });
            const result = await response.json();
            console.log("Start API Response:", result);
        } catch (error) {
            console.error("Failed to start bot:", error);
        }
    };

    const handleStop = async () => {
        console.log("Sending STOP command...");
        try {
            const response = await fetch(`${API_BASE_URL}/stop`, {
                method: 'POST',
            });
            const result = await response.json();
            console.log("Stop API Response:", result);
        } catch (error) {
            console.error("Failed to stop bot:", error);
        }
    };
    
    const isRunning = botData?.bot_status === "RUNNING" || botData?.bot_status === "STARTING";

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <h1>🚀 Trader-Baddu Command Center 🚀</h1>
                <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                    {isConnected ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
                </div>
            </header>

            <div className="controls-section">
                <select 
                    value={selectedAsset} 
                    onChange={(e) => setSelectedAsset(e.target.value)}
                    disabled={isRunning}
                >
                    <option value="NIFTY">NIFTY</option>
                    <option value="CRUDEOIL">CRUDEOIL</option>
                    <option value="NATURALGAS">NATURALGAS</option>
                </select>
                <button onClick={handleStart} disabled={isRunning}>
                    ▶️ START
                </button>
                <button onClick={handleStop} disabled={!isRunning}>
                    ⏹️ STOP
                </button>
            </div>

            <div className="status-grid">
                <div className="status-card">
                    <h2>Bot Status</h2>
                    <p className={`status-text status-${botData?.bot_status?.toLowerCase()}`}>
                        {botData?.bot_status || '...'}
                    </p>
                </div>
                <div className="status-card">
                    <h2>Asset</h2>
                    <p>{botData?.asset || 'N/A'}</p>
                </div>
                <div className="status-card">
                    <h2>ATM Strike</h2>
                    <p>{botData?.ui_state?.atm_strike || 'N/A'}</p>
                </div>
                <div className="status-card">
                    <h2>Last Signal</h2>
                    <p>{botData?.ui_state?.last_signal || '...'}</p>
                </div>
            </div>

            <div className="data-section">
                <div className="data-card">
                    <h2>Live Prices</h2>
                    <pre>{JSON.stringify(botData?.live_prices, null, 2)}</pre>
                </div>
                <div className="data-card">
                    <h2>Positions</h2>
                    <pre>{JSON.stringify(botData?.positions, null, 2)}</pre>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
