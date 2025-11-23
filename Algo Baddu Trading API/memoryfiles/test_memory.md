# Trader-Baddu Project Context

## Project Overview
- **Name**: Trader-Baddu
- **Phases**: 3

## Phase Details

### Phase 1 (Completed)
- **Strategy**: V25
- **Backtested On**: NIFTY index candles
- **Indicators Used**: MACD + EMA21 + ATR trailing SL
- **Take Profit Levels**: TP1/TP2

### Phase 2 (Current)
- **Objective**: Paper-trading backtester using NIFTY Option candles (ATM/ITM CE/PE) instead of index candles
- **Tasks**:
  - Fetch historical option OHLC
  - Run Strategy V25 unchanged (signal logic remains the same)
  - Simulate entries/exits
  - Log trades and P&L

### Phase 3 (Future)
- **Objective**: Live forward testing
- **Execution Method**: Live execution via Dhan_Tradehull (custom wrapper, not vanilla dhanhq)

## Repository Layout (Key Files)
- `Dhan_Tradehull.py` – SDK wrapper (must stay clean, no credentials)
- `data_fetcher.py` – index/option OHLC adapters
- `paper_trader.py` – paper executor & logs (glues Strategy V25)
- `order_manager.py` – ATM/OTM/ITM symbol resolution
- `strategy_v25.py` – MACD+EMA+ATR strategy logic (proven in Phase 1)
- `config.py` – credentials (CLIENT_ID, TOKEN)
- `Dependencies/all_instrument YYYY-MM-DD.csv` – option instrument master
- `tests/smoke_test.py` – sanity tests

## Data Sources
- **Instrument Master CSV Expected Columns**:
  - SEM_TRADING_SYMBOL
  - SEM_CUSTOM_SYMBOL (UNDERLYING)
  - SEM_EXM_EXCH_ID
  - SEM_SMST_SECURITY_ID
  - SEM_STRIKE_PRICE
  - SEM_OPTION_TYPE
  - SEM_EXPIRY_DATE