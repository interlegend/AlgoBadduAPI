# Filter Battle Royale: Experiment Log

This log documents the performance of different filters applied to `StrategyV27` to find the optimal configuration.

**Target Performance:**
*   **Win Rate:** > 58%
*   **Avg P&L:** > ₹350
*   **Total Trades:** > 300
*   **Drawdown Reduction:** > 10% vs Baseline

---

## 1. Baseline: Choppiness Index

*   **Parameters:** Period=14, Threshold=61.8 (assumed default)
*   **Win Rate:** 53.02%
*   **Total Trades:** 796
*   **Avg P&L:** ₹241.42
*   **Max Drawdown:** ₹-10,109.25
*   **Profit Factor:** 1.65
*   **Verdict:** BASELINE ESTABLISHED.

---

## 2. Challenger A: ADX (Average Directional Index)

*   **Parameters:** Period=14, Threshold > 25
*   **Win Rate:** 51.17%
*   **Total Trades:** 428
*   **Avg P&L:** ₹207.29
*   **Max Drawdown:** ₹-10,190.25
*   **Profit Factor:** 1.53
*   **Verdict:** FAIL. The filter is too restrictive and degrades performance across all key metrics.

---

## 3. Challenger B: Bollinger Band Width

*   **Parameters:** Period=20, StdDev=2, Threshold > 0.02
*   **Win Rate:** 0%
*   **Total Trades:** 0
*   **Avg P&L:** ₹0
*   **Max Drawdown:** ₹0
*   **Profit Factor:** 0
*   **Verdict:** FAIL. Filter is far too restrictive at this threshold, resulting in zero trades.

---

## 4. Challenger C: Vortex Indicator (VI)

*   **Parameters:** Period=14, VI_Plus > VI_Minus & Widening Gap
*   **Win Rate:** 55.01%
*   **Total Trades:** 609
*   **Avg P&L:** ₹308.48
*   **Max Drawdown:** ₹-8,423.25
*   **Profit Factor:** 1.85
*   **Verdict:** STRONG CONTENDER. Significant improvement in P&L, Drawdown, and Profit Factor. Win rate also increased.

---

## 5. Challenger D: RSI Regime Filter

*   **Parameters:** Period=14, CE Range=(50, 70), PE Range=(30, 50)
*   **Win Rate:** 54.97%
*   **Total Trades:** 664
*   **Avg P&L:** ₹288.25
*   **Max Drawdown:** ₹-9,417.75
*   **Profit Factor:** 1.78
*   **Verdict:** IMPROVEMENT, BUT NOT CHAMPION. Better than baseline, but Vortex is superior.

---

## Optimization Round 1: EMA Settings (Vortex Period = 14)

| EMA Period | Win Rate | Avg P&L | Total Trades | Max Drawdown | Profit Factor | Verdict |
| :--- | :--- | :--- | :--- |:--- |:--- |:--- |
| 13 (Base)  | 55.01%   | ₹308.48 | 609          | ₹-8,423.25   | 1.85          | Baseline for V28 |
| 21         | 55.26%   | ₹321.14 | 608          | ₹-5,821.50   | 1.90          | **NEW CHAMPION** |
| 9          | 55.01%   | ₹308.48 | 609          | ₹-8,423.25   | 1.85          | No Improvement |

**DECISION:** EMA 21 is the new champion. It provides the best risk-adjusted return. Proceeding to Vortex Tuning with EMA fixed at 21.

---

## Optimization Round 2: Vortex Tuning (EMA = 21)

| Vortex Period | Win Rate | Avg P&L | Total Trades | Max Drawdown | Profit Factor | Verdict |
| :--- | :--- | :--- | :--- |:--- |:--- |:--- |
| 14         | 55.26%   | ₹321.14 | 608          | ₹-5,821.50   | 1.90          | Baseline for this round |
| 10         | 55.01%   | ₹308.48 | 609          | ₹-8,423.25   | 1.85          | Worse than V14 |
| 21         | 57.30%   | ₹335.05 | 541          | ₹-5,526.00   | 1.95          | **ULTIMATE CHAMPION** |

**FINAL DECISION:** The optimal parameter set is **EMA 21** and **Vortex 21**. This combination provides the highest win rate, highest average P&L, and lowest drawdown observed.

---

## Hyper-Optimization Round: SL/TP/Trail Test

### SL_MULTIPLIER Test (EMA=21, VI=21, TP=10, Trail=0.5)
* **SL Multiplier:** 1.2 | **TP (Points):** 10 | **Trail Multiplier:** 0.5
* **Win Rate:** 57.30%
* **Avg P&L:** ₹335.05
* **Total Trades:** 541
* **Max Drawdown:** ₹-5,526.00
* **Verdict:** Baseline for this round.

* **SL Multiplier:** 1.5 | **TP (Points):** 10 | **Trail Multiplier:** 0.5
* **Win Rate:** 58.15%
* **Avg P&L:** ₹344.82
* **Total Trades:** 535
* **Max Drawdown:** ₹-7,143.00
* **Verdict:** PASS - New Champion.

* **SL Multiplier:** 2.0 | **TP (Points):** 10 | **Trail Multiplier:** 0.5
* **Win Rate:** 62.47%
* **Avg P&L:** ₹353.49
* **Total Trades:** 485
* **Max Drawdown:** ₹-8,679.00
* **Verdict:** **MISSION COMPLETE!** - Exceeds all targets.

---