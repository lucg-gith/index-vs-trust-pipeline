# Spec: Build fact_manager_tenure_performance (Gold)

## Purpose
Answer the secondary question: did a trust's performance change when its manager changed.

## Single Responsibility
Aggregates monthly performance within each manager's own tenure span, and compares it to the primary benchmark over the identical span. Does not touch anything about instrument selection or ranking.

## Inputs
`gold.fact_monthly_performance`, `gold.dim_manager`, `gold.dim_financial_instrument` (to find the `is_primary_benchmark` instrument)

## Outputs
`gold.fact_manager_tenure_performance` — grain: one row per `manager_key` (1:1 with `dim_manager`).

| column | type | notes |
|---|---|---|
| manager_key | FK | |
| tenure_return, tenure_annualized_return, tenure_volatility | double | computed over `effective_start_date`–`effective_end_date` |
| index_return_same_period | double | SPY's return over the identical span — **must filter `dim_financial_instrument.is_primary_benchmark = true`, never average across all 4 trackers** |
| alpha_vs_index | double | `tenure_return - index_return_same_period` |

## Transformation / business rules
Kept as a fact separate from `dim_manager` on purpose (not columns bolted onto the dimension) — dimensions describe, facts measure. This distinction is a deliberate modeling choice worth being able to explain, not an accident of how the tables happened to get built.

## Idempotency
Full overwrite.

## Data quality checks
- Every row in `dim_manager` should have a corresponding row here.
- `index_return_same_period` values should be identical for two different managers whose tenure spans happen to fully overlap — if they differ, the benchmark filter logic has a bug.

## Open questions
None.
