# Trader-Baddu Project Repository Structure

## Root Directory
- `QWEN.md`
- `test_memory.md`
- `repo_memory.md` (this file)

## Main Project Directory: `TB DHAN API ALGO`

### Core Files
- `backtest.py`
- `config.py` - Contains CLIENT_ID, ACCESS_TOKEN, LOT_SIZE, TP_POINTS, SL_MULTIPLIER, INTERVAL
- `data_collector.py`
- `data_fetcher.py` - Fetches NIFTY and option OHLC data, manages Tradehull client
- `dhan_check_class.py`
- `Dhan_Tradehull.py` - Custom SDK wrapper for Dhan API
- `live.py`
- `main.py`
- `order_manager.py` - Resolves ATM/ITM/OTM option symbols
- `order_managerperp.py`
- `paper_trader.py` - Paper trading engine that uses Strategy V25
- `repo_map.txt`
- `sdktest.py`
- `smoketest.py`
- `strategy_v21.py`
- `strategy_v25.py` - Core trading strategy with MACD+EMA+ATR logic
- `V25Trade_Log.csv`

### Core Module (`core/`)
- `candle_data.py`
- `indicators.py`
- `instrument_loader.py`
- `logging_config.py`
- `token_guard.py`

### Dependencies (`Dependencies/`)
- `all_instrument 2025-09-10.csv` - Instrument master file
- `log_files/` (directory)

### Tests (`tests/`)
- `smoke_test.py`
- `test_candle_std.py`
- `test_errors.py`
- `test_indicators.py`

## Strategy V25 Details
- Uses MACD, EMA21, and ATR indicators
- Entry signals: BUY_CE and SELL_PE based on MACD histogram patterns
- Exit logic includes initial SL, TP1, and trailing SL after TP1
- No TP2 logic in current implementation

## Paper Trader Details
- Simulates trades using Strategy V25 logic
- Fetches option OHLC data for ATM CE/PE options
- Logs trades to `trade_logs/PaperTrade.csv`
- Implements proper timezone handling (IST)
- Uses Tradehull client for data fetching

## Data Fetcher Details
- Manages Tradehull client initialization
- Fetches NIFTY index OHLC data
- Fetches option OHLC data
- Handles timezone conversion and data normalization
- Implements retry logic for symbol fetching

## Order Manager Details
- Resolves ATM option symbols based on spot price
- Uses instrument master CSV file
- Normalizes instrument data column names
- Finds nearest strike price (nearest 50)