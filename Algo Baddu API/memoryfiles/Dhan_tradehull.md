# MISSION DOSSIER: dhan_tradehull_memory.md

This document contains the complete intelligence breakdown of the `Dhan_Tradehull.py` SDK wrapper. This is the official syntax and function reference for all Z-Fighters.

## 1. Class Overview & Initialization

-   **Class:** `DhanTrade`
-   **Purpose:** Acts as a high-level wrapper around the `dhanhq` library to simplify authentication, data fetching, and order placement.
-   **Initialization:**
    ```python
    client = DhanTrade(
        client_id='YOUR_CLIENT_ID',
        access_token='YOUR_ACCESS_TOKEN',
        instrument_path='path/to/all_instrument.csv'
    )
    ```
-   **Key Attributes:**
    -   `self.dhan`: The raw, underlying `dhanhq` client object.
    -   `self.instrument_df`: A pandas DataFrame containing the full, loaded instrument master file.

## 2. Key Intelligence: The `instrument_exchange` Dictionary

This is the dictionary that caused our `KeyError`. It maps the short exchange names used in function calls to the full names used in the instrument master CSV.

-   **Location:** Defined inside the `DhanTrade` class.
-   **Mapping:**
    -   `'NSE'`: `'NSE'`
    -   `'BSE'`: `'BSE'`
    -   `'NFO'`: `'NFO'`
    -   `'MCX'`: `'MCX'`
-   **CRITICAL FLAW:** There is no key for `'INDEX'`. The SDK expects `'NSE'` for NIFTY index data.

## 3. Core Methods Analysis

### Data Fetching

**`get_intraday_data(self, tradingsymbol, exchange, instrument_type, interval)`**
-   **Purpose:** The primary function for fetching historical OHLC data.
-   **Parameters:**
    -   `tradingsymbol` (str): The symbol to fetch (e.g., `'NIFTY 50'`).
    -   `exchange` (str): The exchange segment. **Must be one of `'NSE', 'BSE', 'NFO', 'MCX'`.**
    -   `instrument_type` (str): The type of instrument (e.g., `'EQUITY'`, `'FUTURE'`, `'OPTION'`).
    -   `interval` (str): The candle timeframe (e.g., `'1'`, `'5'`, `'15'`).
-   **Returns:** A pandas DataFrame with OHLC data.
-   **Note:** This function contains the logic that caused our `KeyError`.

**`get_nifty_ohlc(self, interval)` & `get_banknifty_ohlc(self, interval)`**
-   **Purpose:** These are simple wrapper functions that call `get_intraday_data` with pre-filled parameters for NIFTY and BANKNIFTY respectively. They are the source of our current bug, as they incorrectly pass `'INDEX'` to the `exchange` parameter.

### Order Management

**`place_order(self, security_id, exchange, transaction_type, quantity, order_type, product_type, price)`**
-   **Purpose:** Places a trade order.
-   **Parameters:** Uses specific integer and string codes for `transaction_type` (BUY/SELL), `order_type` (LIMIT/MARKET), etc.
-   **Returns:** An order response dictionary from the API.

**`get_order_book(self)` & `get_trade_book(self)` & `get_positions(self)`**
-   **Purpose:** Standard functions to retrieve information about current orders, executed trades, and open positions.
-   **Returns:** API response dictionaries.

## 4. Authentication Flow

-   The class is initialized with a `client_id` and `access_token`.
-   It uses these credentials to create a `dhanhq` instance.
-   It does **NOT** handle token generation or refresh. This must be done externally and the valid token must be passed in during initialization.