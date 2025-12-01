
# MISSION REPORT: DATA LAG FIX & DAILY GATE REPAIR

## 1. Executive Summary
The discrepancy between the Live Dashboard (Live Pulse) and the Signal Checking logic was caused by a **Critical Data Gap**. 
*   **The Issue**: The Upstox `historical-candle` API (used for warm-up) only provided data up to the *previous* trading session (e.g., Friday). It did *not* include the current day's intraday candles.
*   **The Consequence**: The system started "cold" for the current day (0 candles).
    *   This triggered the **Daily Candle Gate** (which blocks signals if candles < 13), preventing any trades.
    *   The Signal Logic used the last known closed candle (Friday's), causing massive lag in indicator values compared to the Live Pulse (which uses real-time ticks).
*   **The Fix**: Upgraded `live_data_streamer.py` to perform a **Dual-Source Warm-Up**:
    1.  Fetch **Historical Data** (Past Days) to build the long-term buffer.
    2.  Fetch **Intraday Data** (Today) using the specific V3 Intraday endpoint (`/historical-candle/intraday/...`) to fill the gap up to the current minute.
    3.  **Merge & Deduplicate** both datasets to create a seamless, up-to-date history.

## 2. Key Changes
### `live_data_streamer.py`
*   Modified `initialize_warmup` to query `https://api.upstox.com/v3/historical-candle/intraday/{key}/minutes/5`.
*   Implemented `_process_historical_candles_merged` to handle timestamp deduplication between the two sources.

## 3. Verification Results (Smoke Test)
*   **Test Scenario**: MCX CRUDEOIL (Live Market).
*   **Before Fix**:
    *   Warm-up loaded 0 candles for "Today".
    *   Gate Blocked (`Only 1/13 candles`).
    *   Indicators stuck on Friday's close.
*   **After Fix**:
    *   Warm-up loaded **1074 Historical** + **169 Intraday** candles.
    *   Gate **PASSED** (`WARM-UP COMPLETE`).
    *   Indicators synced (Live: `5326.8`, Signal: `5326.63`).
    *   System successfully entered Live Scanning mode.

## 4. Action Required
*   No further action. The system is now self-correcting and handles "mid-day starts" correctly.
