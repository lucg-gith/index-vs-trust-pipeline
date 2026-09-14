# Spec: Discover Trust Universe (Bronze)

## Purpose
Build the starting list of UK investment trusts to evaluate, without relying on any external "best of" ranking, so the eventual top-20 selection is something the pipeline computes itself rather than something curated by a third party.

## Single Responsibility
Produces a reference list of trust names and their resolved LSE tickers. Does not download price history (that's `ingest_trust_prices`) and does not rank or filter by performance (that's `select_top20_trusts` in Silver).

## Inputs
- Wikipedia category page: "Investment trusts of the United Kingdom" (~123 trusts, freely reusable content)
- Each trust's own Wikipedia infobox, for its ticker (most UK investment trust infoboxes list the LSE ticker directly)

## Outputs
`bronze.trust_universe_raw` — grain: one row per trust.

| column | type | notes |
|---|---|---|
| trust_name | string | as listed on the Wikipedia category page |
| ticker | string | resolved LSE ticker, e.g. `SMT.L`; null if it couldn't be resolved automatically |
| source_url | string | the Wikipedia page the ticker was resolved from, for traceability |

## Transformation / business rules
1. Pull the full list of trust names from the Wikipedia category page.
2. For each name, look up its own Wikipedia article and extract the ticker from the infobox where present.
3. Do not hand-curate or filter this list by any performance/quality judgment — completeness here is what makes the later ranking-based selection defensible ("we computed the best 20, we didn't pick them").
4. Any trust whose ticker can't be resolved automatically should be left with `ticker = null` rather than guessed — a human can fill gaps later, but the notebook itself should never invent a ticker.

## Idempotency
Full overwrite. This is a small, mostly-static reference list; re-running it should simply refresh the pull, not accumulate duplicates.

## Data quality checks
- Confirm the total row count is in the expected range (~123); a large deviation suggests the category page structure changed.
- Report the count of unresolved tickers explicitly (don't silently drop them) — this is a case where a human may need to fill in one or two by hand afterward.

## Open questions
- Exact scraping/parsing approach for pulling Wikipedia infobox tickers reliably at scale isn't implemented yet.
