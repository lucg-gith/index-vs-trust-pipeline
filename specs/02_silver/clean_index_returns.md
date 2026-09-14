# Spec: Clean Index Returns (Silver)

## Purpose
Turn the raw, string-typed Bronze index price data into a properly typed, calculated return series usable for real analysis.

## Single Responsibility
Casts types and computes daily/cumulative return fields for the 4 index trackers. Does not decide which one is the primary benchmark (that's a `dim_financial_instrument` attribute in Gold) and does not aggregate to monthly grain (that's Gold's `fact_monthly_performance`).

## Inputs
`bronze.index_prices_raw`

## Outputs
`silver.index_returns` — grain: one row per (ticker, trading day).

| column | type | notes |
|---|---|---|
| trade_date | date | cast from the string Date column |
| ticker | string | |
| close_price | double | cast from string |
| dividend_amount | double | cast from string |
| daily_return | double | computed |
| cumulative_return | double | computed |

## Transformation / business rules
1. Explicitly cast every Bronze string column to its real type (`date`, `double`) — this is where Bronze's deliberately-loose typing gets resolved on purpose.
2. Compute daily return per ticker using a window function (`lag()` over `ticker` ordered by `trade_date`) to compare each day's price to the prior day's.
3. Compute cumulative return as a running product of `(1 + daily_return)` per ticker, again via a window function — this is exactly the kind of calculation the window-functions/CTEs approach is for.
4. **Total return must include dividends.** A day with a dividend payment should not show as a price drop with no offsetting return — the dividend amount needs to be added back into that day's return calculation, or the whole point of choosing SPY over `^GSPC` is undone at this step.

## Idempotency
Full overwrite — cheap to fully recompute from Bronze every run.

## Data quality checks
- No null `close_price` on any row Bronze actually returned data for.
- Daily return values should fall within a sane range (e.g., no single-day return beyond ±30% for one of these ETFs) — anything outside that warrants investigation, not silent inclusion.

## Open questions
None.
