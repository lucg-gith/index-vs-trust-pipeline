# Spec: Discover Trust Universe (Bronze)

## Purpose
Build the starting list of UK investment trusts to evaluate, without relying on any external "best of" ranking, so the eventual top-20 selection is something the pipeline computes itself rather than something curated by a third party.

## Single Responsibility
Loads a human-curated reference list of trust names and tickers into Bronze. Does not download price history (that's `ingest_trust_prices`) and does not rank or filter by performance (that's `select_top20_trusts` in Silver).

## Inputs
`data/trust_universe_seed.csv` — hand-curated, columns: `trust_name, ticker, aic_sector, source_url`.

**Deliberately not automated:** an earlier version of this spec called for scraping ticker values out of Wikipedia infoboxes per trust. That was dropped — infobox formats aren't consistent trust-to-trust, so a scraper would be fragile, and this is a small (~123 rows), static, one-time list that doesn't justify the engineering cost of reliable automated parsing. The trust *names* came from Wikipedia's "Investment trusts of the United Kingdom" category (freely reusable content, pulled once); tickers and sectors are filled in by hand from the AIC's member directory (manual browsing only — their Terms of Use explicitly ban automated scraping) or a per-name search as a fallback.

## Outputs
`bronze.trust_universe_raw` — grain: one row per trust. Same four columns as the seed CSV, cast to string per the usual Bronze convention.

## Transformation / business rules
1. Read `data/trust_universe_seed.csv` as-is.
2. Do not hand-curate or filter this list by any performance/quality judgment beyond what the source category already implied — completeness here is what makes the later ranking-based selection defensible ("we computed the best 20, we didn't pick them").
3. A trust whose `ticker` is still blank in the CSV passes through as null — the notebook should never invent a ticker.

## Idempotency
Full overwrite. Re-running it just re-reads the current state of the seed CSV.

## Data quality checks
- Confirm the total row count matches the seed CSV (~123); a mismatch means a read/parse problem, not a source-side issue.
- Report the count of blank tickers explicitly (don't silently drop them) — those rows need the manual lookup pass completed before `ingest_trust_prices` can use them.

## Open questions
None — approach settled. Filling in the remaining ticker/sector values in the CSV is manual work in progress, not a design question.
