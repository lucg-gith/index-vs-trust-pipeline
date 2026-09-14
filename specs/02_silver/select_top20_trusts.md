# Spec: Select Top 20 Trusts (Silver)

## Purpose
Determine which 20 trusts actually move forward into the rest of the pipeline, using a criterion the pipeline computes itself rather than an externally curated "best of" list.

## Single Responsibility
Computes trailing return per trust and ranks them. Does not clean/adjust the underlying price data itself (that's `clean_trust_returns`) and does not decide anything about manager history.

## Inputs
`bronze.trust_prices_raw` (or `silver.trust_returns`, if this step ends up running after basic cleaning — sequencing to be fixed at implementation time, but the ranking logic itself doesn't change either way)

## Outputs
An `overall_rank` and `is_top20` flag, ultimately landing on `gold.dim_financial_instrument`, but computed here in Silver as an intermediate result.

## Transformation / business rules
1. **Filter to `is_active = true` first.** `bronze.trust_universe_raw` includes trusts that have since been delisted, wound up, or merged away — their price history simply stops on whatever date that happened, so an unfiltered "15-year return" for one of them is meaningless, not just noisy. Ranking must never consider an inactive trust.
2. Compute trailing 15-year total return per trust (dividend-inclusive), for whatever trusts remain after that filter.
3. Rank trusts by that return using a window function: `rank() over (order by trailing_return desc)`.
4. Flag the top 20 as `is_top20 = true`.
4. This selection is a one-time snapshot decision for the project, not something that needs to be recomputed on every scheduled pipeline run — but the query itself should still be written idempotently (same inputs → same ranking) in case it is re-run.

## Idempotency
Deterministic computation — the same input data always produces the same ranking. No side effects to worry about beyond the usual overwrite-the-output pattern.

## Data quality checks
- A trust with too little price history to compute a meaningful 15-year return (e.g., listed only 2 years ago) should be handled explicitly — either excluded from ranking with a clear reason logged, or ranked using whatever partial history it has, but not silently miscounted as a "full 15-year winner."

## Open questions
- Whether trusts with partial history should be excluded entirely or ranked on a shorter comparable window isn't decided yet.
