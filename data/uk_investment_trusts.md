Quick rundown on how I got the manager names for the UK investment trusts file:

Source: Each trust's AIC (Association of Investment Companies) page — theaic.co.uk/companydata/<trust-slug>. Same source_url column I'd already built out for the tickers/sectors.

Method: Used a browser session to fetch the raw HTML of each of the 120 AIC pages (same-origin fetch, so no CORS issues), then regex-extracted the "Fund manager" and "Management group" fields straight out of the rendered page structure. Ran it in batches of ~20-25 pages at a time with a small delay between requests to be polite to their server.

Coverage: 97/120 trusts got a named manager, 99/120 got a management group.

Exceptions (6 trusts): Their AIC page had gone dead or redirected to a 404 — turned out these were all recent corporate actions: Apax Global Alpha (delisted after a take-private deal, Sept 2025), BlackRock Throgmorton (merged into BlackRock Smaller Companies, Apr 2026), Bluefield Solar (delisted post-Drax takeover), European Opportunities Trust (wound down, rolled into JPMorgan European Growth & Income), Henderson European Trust (merged with Fidelity European Trust), and North Atlantic Smaller Companies (not actually an AIC member — pulled that one from the trust's own site + Harwood Capital instead). Confirmed each via a quick web search and noted it in the CSV's notes column.

Still blank (18 rows): The trusts that never had an AIC companydata URL to begin with — the ones already flagged in the original file as delisted/wound-up/merged, sourced from Wikipedia etc. Left those blank rather than guess.

One thing worth knowing for the project write-up: a few "Fund manager" fields list a full team rather than one lead name (e.g. NB Private Equity Partners has 12 names) — that's exactly what AIC publishes, not a parsing artifact.