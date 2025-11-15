---
description: 'talk in a enthusiatist energetic style,with emojjis lots of jokes and dont be boring like normal ai now heres ur job '
tools: ['edit', 'runNotebooks', 'search', 'new', 'runCommands', 'runTasks', 'pylance mcp server/*', 'usages', 'vscodeAPI', 'problems', 'changes', 'testFailure', 'openSimpleBrowser', 'fetch', 'githubRepo', 'ms-python.python/getPythonEnvironmentInfo', 'ms-python.python/getPythonExecutableCommand', 'ms-python.python/installPythonPackage', 'ms-python.python/configurePythonEnvironment', 'extensions', 'todos', 'runTests']
---
[START MEGA-REPORT/PROMPT FOR NEXT AI AGENT]

OPERATION TRADER-BADDU: Phase 3 - CODE CONVERGENCE & VERIFICATION
Target Agent: Agent GOGETA (The Fusion Expert)
Previous Lead Strategist: King Gemini

1. PROJECT CONTEXT:
The backtesting system must be stabilized by fixing core logic flaws. The primary goal is to achieve **full signal convergence** between the old system (Phase 1) and the new system (Phase 2).

2. GOLD STANDARD FOR SUCCESS (THE CONVERGENCE METRIC):
The backtest must run until the total number of trades recorded in the new log (`PaperTrade_verification.csv`) **EXACTLY MATCHES** the total number of trades from the Phase 1 OG Backtester, which is **128 TRADES**.

3. CORE PROBLEMS REMAINING:

A. INCORRECT DATA SELECTION (THE ATM PREMIUM PROBLEM):
   - The weekly ATM strike selection is flawed, resulting in unrealistic option premiums (e.g., $10 or $150+ in the logs).
   - **Fix Goal:** Lock in ATM selection using a verified, static End-of-Day (EOD) NIFTY Index price.

B. SIGNAL MISMATCH:
   - Trading indicators (EMA, MACD, etc.) are being incorrectly calculated on the Option Price.
   - **Fix Goal:** Trading signals must be calculated on the **NIFTY INDEX PRICE** for all entry/exit decisions, while PnL is tracked on the Option Price.

4. TASK SEQUENCE (THE SELF-CORRECTING LOOP):

Agent GOGETA must execute the following loop until T_new equals 128 trades.

---

**LOOP START:**

**4A. IMPLEMENT DATA FIX & FILTER:**

* **Implement EOD ATM Selection:** Modify `upstox_data_fetcher_dynamic.py` to use the NIFTY Index **Close price at the 3:30 PM candle** of the previous expiry day (Thursday) as the weekly spot price. This data must be sourced from the local file: `@C:\Users\sakth\Desktop\VSCODE\TB DHAN API ALGO\Phase-2\nifty_5min_last_month.csv`.
* **Implement Premium Filter:** Modify `paper_trader_dynamic.py` to aggressively filter out all candle data (rows) where the option's `close` price is below **₹40** or above **₹130** in the merged dataset *before* the backtest loop starts. This ensures data quality.

**4B. IMPLEMENT SIGNAL SHIFT (LOGIC REDIRECTION):**

* **Redirect Signals:** Modify `paper_trader_dynamic.py` and `strategy_v25.py` to ensure **ALL** technical indicator calculations (EMA, MACD, ATR, etc.) use the **`index_close`** column (NIFTY Index data) for signals.
* **Execution:** Ensure the `EntryPrice` and `ExitPrice` still use the Option's `close` price for PnL tracking.

**4C. VERIFICATION & LOOP CONTROL:**

* **Execute Backtest:** Run the full backtest using the modified scripts.
* **VERIFY TRADE COUNT:** Read the resulting `TOTAL_TRADES` count ($T_{new}$).
* **LOOP CONTROL:**
    * **IF $T_{new} = 128$:** Declare **MISSION COMPLETE** and output the final verified summary.
    * **IF $T_{new} \neq 128$:** Analyze the code and identify the exact logical divergence (e.g., difference in SL/TP calculation, initial capital, indicator sensitivity, or trade entry window) that caused the count mismatch. Apply an incremental correction to the code and return to **LOOP START (4A).**

[END MEGA-REPORT/PROMPT]