# Spec: Build dim_manager (Gold)

## Purpose
Expose the SCD2 manager-history dimension at the Gold layer, joined to its parent instrument.

## Single Responsibility
Passes through `silver.trust_manager_history`, resolving `trust_ticker` to `instrument_key`. Does not compute any performance measures — see `fact_manager_tenure_performance` for that.

## Inputs
`silver.trust_manager_history`, `gold.dim_financial_instrument` (for the ticker → instrument_key lookup)

## Outputs
`gold.dim_manager` — grain: one row per (trust, tenure span). Columns: `manager_key, instrument_key, manager_name, management_group, effective_start_date, effective_end_date, is_current, history_researched`.

## Transformation / business rules
Straightforward join/passthrough from Silver — all the real business logic (the versioning rule, the manual sourcing) lives upstream in `load_manager_history`. This notebook's only real job is resolving the ticker to a surrogate `instrument_key` so it can be joined cleanly elsewhere in Gold.

## Idempotency
Full overwrite is fine at this layer even though the Silver table underneath used `MERGE` — Gold is rebuilt fresh from Silver's already-correct state each time.

## Data quality checks
Every `trust_ticker` from Silver must resolve to exactly one `instrument_key` — an unresolved ticker here means something upstream (universe discovery, top-20 selection) is out of sync with the manager-history data and needs investigating, not silently dropping.

## Open questions
None.
