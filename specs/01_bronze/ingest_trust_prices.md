# Spec: Ingest Trust Prices (Bronze)

## Purpose
Capture 15 years of daily price and distribution history for every trust in the discovered universe, so the ranking/selection step downstream has real performance data to work from.

## Single Responsibility
Downloads raw daily OHLCV + dividends/splits data for every ticker in `bronze.trust_universe_raw` and writes it to one Bronze table. Does not decide which trusts make the top 20 — that's a Silver concern.

## Inputs
- `bronze.trust_universe_raw` (tickers to pull)
- Yahoo Finance via `yfinance`

## Outputs
`bronze.trust_prices_raw` — grain: one row per (ticker, trading day). Same column shape as `bronze.index_prices_raw` (Date, Open, High, Low, Close, Adj_Close, Volume, Dividends, Stock_Splits, Capital_Gains, ticker), all stored as strings for the same reason.

## Transformation / business rules
Identical pattern to `ingest_index_prices`, looped over every resolved ticker in the trust universe instead of the fixed 4-ticker index list — this notebook should reuse the same column-rename, timezone-strip, and string-cast logic rather than reimplementing it (Open/Closed: the only thing that changes is the list being looped over).

**Critical operational rule:** download tickers **sequentially, one at a time**, never in parallel across Spark executors. Yahoo Finance's endpoint is not a sanctioned public API — it's what `yfinance` scrapes — and blocks aggressively under concurrent load. A sequential loop over ~120 tickers takes a couple of minutes; this is a one-time historical backfill, not a job where that time matters.

## Idempotency
Full overwrite. Same reasoning as the index prices notebook — cheap to fully re-derive.

## Data quality checks
- Log and report any ticker that fails to download (delisted, renamed, or a bad ticker from the universe-discovery step) rather than letting the whole notebook fail.
- Row count per ticker should be close to the expected trading-day count for however much of the 15-year window that trust has actually been listed — a trust listed only 8 years ago should have roughly 8 years of rows, not be treated as an error.

## Open questions
- How to handle a trust that changed ticker symbol during the 15-year window (a real possibility for older trusts) isn't decided yet.
