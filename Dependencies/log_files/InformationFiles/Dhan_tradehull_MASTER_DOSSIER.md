
# MISSION DOSSIER: Dhan_Tradehull SDK (Master Reference v2)

**TO:** Agent Goku (Gemini CLI)
**FROM:** King Gemini (Strategic Command)
**SUBJECT:** Complete Technical Blueprint and Operational Protocol for Dhan_Tradehull.py (v2 - Ground Truth)

This document contains the definitive, ground-truth intelligence on the `Tradehull` Python library. Your understanding of this dossier must be absolute. All function and parameter names herein are verified directly from the source code and are final.

---

## 1. Executive Summary

The `Tradehull` class, located in `Dhan_Tradehull.py`, is a high-level strategic wrapper built around the official `dhanhq` Python library. Its primary purpose is to simplify and streamline all interactions with the Dhan API, including authentication, data fetching, order management, and instrument handling, specifically tailored for the needs of Operation Trader-Baddu.

It is designed to be our single, unified interface for all trading operations.

---

## 2. Class Initialization (The Handshake)

This is the single most critical step. The following is the exact and only way to initialize the `Tradehull` class, confirmed from the source code.

*   **Class Name:** `Tradehull`
*   **Constructor Signature:**
    ```python
    __init__(self, ClientCode:str, token_id:str)
    ```
*   **Parameters:**
    *   `ClientCode` (str): The mandatory Client ID.
    *   `token_id` (str): The mandatory Dhan Access Token.

*   **Correct Usage Example:**
    ```python
    from Dhan_Tradehull import Tradehull

    # Use these exact keyword arguments
    dhan_client = Tradehull(
        ClientCode='YOUR_CLIENT_ID',
        token_id='YOUR_ACCESS_TOKEN'
    )
    ```

---

## 3. Core Methods Deep Dive (The Arsenal)

The following is a complete list of all public methods available within the `Tradehull` class, grouped by function.

### 3.1 Data Fetching

*   **`get_intraday_data(self, tradingsymbol, exchange, timeframe, debug="NO")`**
    *   **Purpose:** The primary method for fetching intraday data. It fetches 1-minute data and resamples it to the desired timeframe.
    *   **Parameters:**
        *   `tradingsymbol` (str): The symbol to fetch (e.g., 'NIFTY 50').
        *   `exchange` (str): The exchange segment (e.g., 'NSE', 'NFO').
        *   `timeframe` (int): The candle timeframe in minutes (e.g., 1, 5, 15).
    *   **Returns:** A pandas DataFrame with OHLCV data, or an empty DataFrame on failure (especially on `DH-905` errors).

*   **`get_historical_data(self, tradingsymbol, exchange, timeframe, debug="NO")`**
    *   **Purpose:** Fetches historical data for a longer lookback period (up to 365 days).
    *   **Returns:** A pandas DataFrame with OHLCV data.

*   **`get_quote_data(self, names, debug="NO")`**
    *   **Purpose:** Fetches full quote data (including OHLC, depth) for a list of symbols.
    *   **Parameters:**
        *   `names` (list or str): A list of symbols to get quotes for.
    *   **Returns:** A dictionary where keys are symbol names and values are dictionaries of quote data.

*   **`get_ltp_data(self, names, debug="NO")`**
    *   **Purpose:** Fetches only the Last Traded Price (LTP) for a list of symbols.
    *   **Parameters:**
        *   `names` (list or str): A list of symbols.
    *   **Returns:** A dictionary where keys are symbol names and values are the LTP.

### 3.2 Order Management

*   **`order_placement(self, tradingsymbol, exchange, quantity, price, trigger_price, order_type, transaction_type, trade_type, ...)`**
    *   **Purpose:** Places a trade order.
    *   **Key Parameters:** `tradingsymbol`, `exchange`, `quantity`, `order_type`, `transaction_type`, `trade_type`.
    *   **Returns:** The `orderId` as a string on success, `None` on failure.

*   **`modify_order(self, order_id, order_type, quantity, price=0, ...)`**
    *   **Purpose:** Modifies a pending order.
    *   **Returns:** The `orderId` as a string on success.

*   **`cancel_order(self, OrderID:str)`**
    *   **Purpose:** Cancels a single pending order.
    *   **Returns:** The order status as a string (e.g., 'CANCELED').

*   **`cancel_all_orders(self)`**
    *   **Purpose:** A comprehensive function to cancel all pending orders and square off all open MIS positions.
    *   **Returns:** A dictionary of order details for the exit orders placed.

### 3.3 Account & Position Information

*   **`get_balance(self)`**
    *   **Purpose:** Retrieves the available trading balance.
    *   **Returns:** The available balance as a float.

*   **`get_live_pnl(self)`**
    *   **Purpose:** Calculates and returns the live, real-time PnL for all open positions.
    *   **Returns:** The total MTM PnL as a float.

*   **`get_positions(self, debug="NO")`**
    *   **Purpose:** Retrieves all open positions.
    *   **Returns:** A pandas DataFrame of the positions.

*   **`get_holdings(self, debug="NO")`**
    *   **Purpose:** Retrieves all holdings.
    *   **Returns:** A pandas DataFrame of the holdings.

*   **`get_orderbook(self, debug="NO")`**
    *   **Purpose:** Fetches the list of all orders for the day.
    *   **Returns:** A pandas DataFrame of the order book.

*   **`get_trade_book(self, debug="NO")`**
    *   **Purpose:** Fetches the details of all trades executed for the day.
    *   **Returns:** A pandas DataFrame of the trade book.

*   **`get_order_detail(self, orderid:str, debug="NO")`**
    *   **Purpose:** Fetches the full details of a specific order by its ID.
    *   **Returns:** A dictionary containing the order details.

### 3.4 Instrument & Option Helpers

*   **`get_instrument_file(self)`**
    *   **Purpose:** Loads the latest instrument master CSV file into the `instrument_df` attribute.

*   **`get_lot_size(self, tradingsymbol: str)`**
    *   **Purpose:** Returns the lot size for a given trading symbol.

*   **`get_expiry_list(self, Underlying, exchange)`**
    *   **Purpose:** Fetches a list of available expiry dates for an underlying.

*   **`get_option_chain(self, Underlying, exchange, expiry, num_strikes=10)`**
    *   **Purpose:** Retrieves the full option chain for a given underlying and expiry.

*   **`ATM_Strike_Selection(self, Underlying, Expiry)`**, **`OTM_Strike_Selection(...)`**, **`ITM_Strike_Selection(...)`**
    *   **Purpose:** High-level functions to resolve CE/PE symbols for ATM, OTM, or ITM strikes.

---

**END OF DOSSIER v2**
