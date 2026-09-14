# Spec: Build dim_date (Gold)

## Purpose
Provide a standard calendar dimension so fact tables can be filtered/grouped by year, quarter, trading-day status, and notable market events.

## Single Responsibility
Generates one row per calendar day across the project's date range. Does not contain any fact/measure data.

## Inputs
None — this is a generated dimension, not sourced from Bronze/Silver.

## Outputs
`gold.dim_date` — grain: one row per calendar day, spanning the full 15-year window.

| column | type | notes |
|---|---|---|
| date_key | int | YYYYMMDD surrogate |
| full_date | date | |
| year, quarter, month, month_name, day_of_week | various | standard calendar attributes |
| is_trading_day | boolean | derived by checking which dates actually appear in `silver.index_returns` |
| market_event | string, nullable | hand-seeded, e.g. "COVID Crash" — not a live feed (see Open questions) |

## Transformation / business rules
1. Generate a complete calendar sequence (a Spark `sequence()` over dates, or an equivalent date-generation approach) covering the full window, not just trading days — this lets `is_trading_day` be a real derived flag rather than an assumption.
2. Hand-seed `market_event` for the handful of events that actually fall inside the window: COVID (2020), the 2022 bear market, Aug 2024 volatility. **Note: the 2008 financial crisis is outside this window** — a straight 15-year lookback from the project's build date lands around 2011, so 2008 will not appear here.

## Idempotency
Full overwrite — this is a generated, deterministic dimension; re-running it should always produce the exact same table.

## Data quality checks
- No gaps in the date sequence.
- `is_trading_day` should roughly match the ~252/year expectation.

## Open questions
- Whether to source `market_event` from FRED's `USREC` series instead of hand-seeding is still open — hand-seeding was the recommended default given how few rows are actually needed, but not yet finalized either way.
