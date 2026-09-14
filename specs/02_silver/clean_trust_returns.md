# Spec: Clean Trust Returns (Silver)

## Purpose
Same job as `clean_index_returns`, applied to the top-20 trust universe.

## Single Responsibility
Casts types and computes return fields for the 20 selected trusts. Reuses the exact same logic as `clean_index_returns` — the only difference is which table it reads from — so this should share code/pattern with that notebook rather than duplicate it with drift risk (Open/Closed in practice: one shared return-calculation routine, applied to two different inputs).

## Inputs
`bronze.trust_prices_raw`, filtered to the 20 trusts flagged `is_top20 = true` by `select_top20_trusts`

## Outputs
`silver.trust_returns` — same column shape as `silver.index_returns` (trade_date, ticker, close_price, dividend_amount, daily_return, cumulative_return).

## Transformation / business rules
Identical to `clean_index_returns` — see that spec. The only trust-specific consideration: some trusts will have shorter history than the full 15-year window (later IPOs), so return calculations naturally start wherever each trust's own data starts, not a fixed date for all 20.

## Idempotency
Full overwrite.

## Data quality checks
Same as `clean_index_returns`, applied per trust. Additionally: confirm every trust flagged `is_top20 = true` actually has a corresponding row set here — a silent drop here would corrupt the whole comparison.

## Open questions
None.
