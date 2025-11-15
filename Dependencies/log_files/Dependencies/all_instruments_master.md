# MISSION DOSSIER: all_instruments_master.md

This document contains the complete intelligence breakdown of the primary instrument data source for Operation Trader-Baddu. All agents must reference this dossier for data-related tasks.

## 1. File Summary

-   **Source File Analyzed:** `all_instrument 2025-09-19.csv`
-   **Total Instruments Listed:** 201,385

## 2. Column Schema Analysis

The following table details the complete structure of the instrument master file.

| Column Name | Data Type (inferred by pandas) |
| :--- | :--- |
| SEM_EXM_EXCH_ID | object |
| SEM_SEGMENT | object |
| SEM_SMST_SECURITY_ID | int64 |
| SEM_TRADING_SYMBOL | object |
| SEM_LOT_UNITS | int64 |
| SEM_EXPIRY_DATE | object |
| SEM_STRIKE_PRICE | float64 |
| SEM_OPTION_TYPE | object |
| SEM_CUSTOM_SYMBOL | object |
| SEM_TICK_SIZE | float64 |
| SEM_EXPIRY_FLAG | object |
| SEM_INSTRUMENT_TYPE | object |
| SEM_PRICE_QUOT_FACTOR | object |
| SEM_PRICE_UNIT | object |
| SEM_GEN_DEN | object |
| SEM_GEN_NUM | object |
| SEM_PRECISION | int64 |
| SEM_QTY_UNIT | object |
| SEM_DELIVERY_UNIT | object |
| SEM_DELIVERY_QTY | float64 |
| SEM_EXERCISE_TYPE | float64 |
| SEM_UNDERLYING_ID | float64 |

## 3. Key Instrument Analysis

-   **Unique Underlyings Found:** `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY`, `NIFTYNXT50`, `USDINR`, and many others.

-   **NIFTY Contract Analysis:**
    -   **Total NIFTY Option Contracts:** 7,130 (CE & PE combined).
    -   **Next 5 Upcoming NIFTY Expiries (from 2025-09-14):**
        1.  `2025-09-18`
        2.  `2025-09-25`
        3.  `2025-10-02`
        4.  `2025-10-09`
        5.  `2025-10-16`

## 4. Data Quality & Risk Assessment

-   **Missing Values:** The columns `SEM_DELIVERY_QTY`, `SEM_EXERCISE_TYPE`, and `SEM_UNDERLYING_ID` contain a significant number of `NaN` (missing) values. This is acceptable as they are not relevant for our operation. All critical columns appear fully populated.
-   **Data Type Risks:**
    -   **(P0 Risk) `SEM_EXPIRY_DATE` is a `string` (object):** All logic must explicitly parse this column into a proper `date` or `datetime` object before use.
    -   **(P1 Risk) `SEM_STRIKE_PRICE` is a `float64`:** Logic should safely cast this to an `int` or `float` before mathematical comparisons to avoid precision errors.