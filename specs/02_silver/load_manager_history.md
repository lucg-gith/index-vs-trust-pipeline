# Spec: Load Manager History (Silver)

## Purpose
Bring the manually-researched trust manager history into the pipeline as a proper SCD2 dimension, since no free bulk source exists for this data (confirmed: AIC and Trustnet both explicitly restrict scraping in their Terms of Use).

## Single Responsibility
Loads and validates a human-curated CSV into a versioned table. Does not do the research itself (see `manager_history_research_playbook.md`) and does not compute any performance metrics from it (that's `fact_manager_tenure_performance` in Gold).

## Inputs
`data/manager_history_seed.csv`, hand-produced per the research playbook, with columns:
`trust_ticker, manager_name, management_group, effective_start_date, effective_end_date, is_current, history_researched, source_url`

## Outputs
`silver.trust_manager_history` — grain: one row per (trust, manager/management-group tenure span).

## Transformation / business rules
1. A new row exists whenever **either** `manager_name` or `management_group` changes for a trust — this is a deliberate modeling choice: a management firm handover and a named-manager handover don't always land on the same date, and tracking both in one row-versioned table avoids two separate SCD2 tables with dates that would need reconciling against each other.
2. For trusts without a deep-dive research pass, exactly one row exists spanning the trust's earliest available price date through to "current" — `history_researched = false` flags this honestly, rather than pretending a single span means "no changes ever happened."
3. **Validate before accepting the load:** no two rows for the same trust should have overlapping date ranges, and exactly one row per trust should have `is_current = true` with a null/open `effective_end_date`.

## Idempotency
This is the one table in the pipeline that **must use `MERGE`, not overwrite or append.** Overwrite would work today, but the moment this CSV needs a correction or an addition, a naive re-run must update existing spans rather than either wiping everything or duplicating rows. Merge key: `(trust_ticker, effective_start_date)`.

## Data quality checks
- No overlapping date ranges per trust (validate with a self-join or window-function check before accepting the load).
- Exactly one current row per trust.
- Every `trust_ticker` in this table exists in the top-20 trust list — a typo'd ticker here should fail loudly, not silently create an orphaned manager history nobody joins to.

## Open questions
None — the CSV format and versioning rule are settled; only the actual research content (which trusts, which dates) remains to be filled in.
