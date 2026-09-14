# Spec: Build dim_financial_instrument (Gold)

## Purpose
Provide one unified dimension covering both the S&P 500 trackers and the trust universe, so a single fact table can hold both sides of the comparison.

## Single Responsibility
Describes each instrument (index tracker or trust) — name, type, ranking, benchmark status. Contains no performance measures.

## Inputs
`silver.index_returns`, `silver.trust_returns` (for the list of instruments and their `is_top20`/ranking attributes)

## Outputs
`gold.dim_financial_instrument` — grain: one row per instrument (4 index trackers + 20 trusts = 24).

| column | type | notes |
|---|---|---|
| instrument_key | surrogate | |
| ticker, name | string | |
| instrument_type | string | `'Index'` or `'Trust'` — the single column that lets one fact table hold both sides of the comparison |
| aic_sector | string, trusts only | |
| overall_rank, is_top20 | trusts only | computed in `select_top20_trusts`, not externally curated |
| is_primary_benchmark | boolean | `true` only for SPY; used by `fact_manager_tenure_performance` to unambiguously define "beating the index" |

## Transformation / business rules
- All 4 index trackers get `instrument_type = 'Index'`; only SPY gets `is_primary_benchmark = true` — SPY was chosen specifically for its 1993 inception, since VOO (2010) barely covers the 15-year window with no margin.
- `overall_rank`/`is_top20` are null/not-applicable for index rows — ranking is a trust-only concept.

## Idempotency
Full overwrite.

## Data quality checks
- Exactly one row with `is_primary_benchmark = true`.
- Exactly 20 rows with `is_top20 = true`.

## Open questions
None.
