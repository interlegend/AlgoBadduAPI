# TODO: Phase 5 - Realism, Optimization, and Production Readiness

This file outlines the next critical steps for evolving the Trader-Baddu backtester into a live-ready trading bot.

## 1. Financial Realism 💰

- [ ] **Implement Commission Model:** Create a function `calculate_net_pnl(gross_pnl)` that deducts ₹50 per order (Brokerage + STT + Exchange Txn Charges).
- [ ] **Update Reporting:** Modify `generate_report` to show Gross P&L vs Net P&L.

## 2. Risk Optimization 🛡️

- [ ] **SL Analysis:** Run a loop testing fixed SL points (10, 15, 20, 25) vs the current 1.2 * ATR dynamic SL to find the "Sweet Spot".
- [ ] **Trailing Stop Upgrade:** The current trail (0.5 ATR) might be too tight, causing premature exits. Test 1.0 ATR trail.

## 3. Production Readiness (Live Algo) 🚀

- [ ] **API Skeleton:** Create `live_trader.py`. Import `dhanhq`. Write the `place_order` function skeleton with JSON payload structure.
- [ ] **Token Management:** Add `.env` file support for `CLIENT_ID` and `ACCESS_TOKEN`.

## 4. Data Integrity 📊

- [ ] **Gap Handling:** Add a check in the loop: if (time_diff > 5 minutes) -> Force Exit Position (Protection against data feed disconnection).
