# Spec: Ingest Index Prices (Bronze)

## Purpose
Capture 15 years of daily price and distribution history for the four S&P 500-tracking ETFs used as the "index" side of the comparison, exactly as the source returns it, with no interpretation applied.

## Single Responsibility
Downloads raw daily OHLCV + dividends/splits/capital-gains data for a fixed list of tickers and writes it to one Bronze table. Does not clean, adjust, compute returns, or decide which ticker is the primary benchmark — those are Silver/Gold concerns.

## Inputs
- Yahoo Finance, via the `yfinance` Python library (an unofficial community library, not a documented/guaranteed API)
- Ticker list: `SPY`, `IVV`, `VOO`, `SPLG` — all track the same underlying S&P 500 index; SPY is the primary benchmark (history to 1993), the other three exist for a secondary "trackers should overlap" cross-check chart

## Outputs
`bronze.index_prices_raw` — grain: one row per (ticker, trading day).

| column | type | notes |
|---|---|---|
| Date | string | Bronze stores everything as a string — see Transformation rules |
| Open, High, Low, Close, Adj_Close | string | raw values as returned by yfinance |
| Volume | string | |
| Dividends, Stock_Splits, Capital_Gains | string | most rows will be "0.0" — these events are rare, not daily |
| ticker | string | which of the 4 tickers this row belongs to |

## Transformation / business rules
1. Pull 15 years of daily history (`period="15y"`) with `auto_adjust=False, actions=True` — raw Close and dividend-adjusted Close must stay separate columns, since dividends are needed explicitly for total-return math later.
2. Reset the pandas index so the date becomes a real column.
3. Replace spaces in column names with underscores (`"Adj Close"` → `"Adj_Close"`) — Delta Lake rejects column names containing spaces.
4. Strip timezone info from the date column — Spark cannot cleanly convert timezone-aware pandas timestamps.
5. Tag every row with its source ticker before combining all 4 into one table.
6. Cast every column to string type before writing. Bronze makes no type decisions — that's Silver's job, and it means ingestion can never fail on an unexpected value from the source.
7. Combine all 4 tickers' data with Spark's `union`, not pandas `concat` — keep the pandas boundary as small as possible; `yfinance` is the only reason pandas appears in this notebook at all.

## Idempotency
Full overwrite (`mode("overwrite")`). Each run re-pulls the complete 15-year window and replaces the table entirely — safe because the dataset is small (~15,000 rows total) and cheap to fully re-derive every time. Never use `append` here.

## Data quality checks
- Row count per ticker should be close to 252 trading days × 15 years (~3,770-3,774); flag if any ticker is significantly short.
- VOO specifically should be checked against its actual inception (Sept 2010) — if the project's date window is later widened, VOO's history may not reach back far enough and it may need to be dropped or handled separately.

## Open questions
None — this notebook is implemented and running.
