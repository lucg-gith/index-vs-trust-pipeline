# Spec: Build fact_monthly_performance (Gold)

## Purpose
Answer the project's headline question: does the S&P 500 outperform the trusts, and which trusts beat it — at monthly grain.

## Single Responsibility
Aggregates daily Silver return data to month-end snapshots for every instrument. Does not touch manager history — see `fact_manager_tenure_performance` for that.

## Inputs
`silver.index_returns`, `silver.trust_returns`, `gold.dim_financial_instrument`, `gold.dim_date`

## Outputs
`gold.fact_monthly_performance` — grain: one row per (instrument_key, month), `date_key` always the last trading day of the month.

| column | type | notes |
|---|---|---|
| instrument_key, date_key | FK | composite key |
| close_price, dividend_amount | double | |
| monthly_return, cumulative_return | double | |
| total_return | double | dividend-inclusive |

## Transformation / business rules
1. Daily data stays daily all the way through Bronze/Silver — this notebook is the only place the grain actually changes, from daily to monthly. Aggregating too early would make it impossible to correctly compute a month-end value (you'd be working from an already-lossy source).
2. `date_key` for each month must be the **last trading day of that month**, not a fixed calendar date, since months don't always end on a trading day.
3. `total_return` must be dividend-inclusive and computed the same way for both the index and trust sides — this is the whole reason SPY (not `^GSPC`) was chosen as the index source; a mismatch here invalidates the entire comparison this table exists to support.

## Idempotency
Full overwrite — rebuilt fresh from Silver every run.

## Data quality checks
- Every instrument in `dim_financial_instrument` should have at least one row here (unless its listing genuinely doesn't cover a given month — e.g., a trust IPO'd partway through the window).
- No duplicate (instrument_key, date_key) pairs.

## Open questions
None.
