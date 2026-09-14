# Implementation Specs

This folder holds one specification per implementation unit in the pipeline — Bronze ingestion notebooks, Silver cleaning steps, Gold table builders. Each spec is written so that anyone picking up the work — a teammate, a future version of yourself, or an AI assistant with no memory of how this project got designed — has everything needed to implement it correctly, without re-deriving decisions that were already made and reasoned through.

## How SOLID applies to a data pipeline

SOLID was written for object-oriented class design, but the underlying discipline translates directly to a set of notebooks and tables:

- **Single Responsibility** — each notebook does exactly one job (ingest one data domain, clean one table, build one dimension/fact). If a spec's "Purpose" needs "and" to describe what it does, it's doing too much.
- **Open/Closed** — extend behavior via configuration (a ticker added to a list, a trust added to the universe), never by rewriting the core logic. The `index_tickers` list in Bronze is the pattern: adding IVV/VOO/SPLG didn't require touching the download/write logic at all.
- **Liskov Substitution** — if a data source is swapped (e.g. `yfinance` replaced by a paid API), the table it produces must keep the same shape and meaning that downstream code depends on. Nothing consuming `bronze.index_prices_raw` should need to change just because *how* it was populated changed.
- **Interface Segregation** — each layer exposes only what the next layer actually needs. Bronze can be wide and raw; Silver should narrow down to what Gold actually consumes, not pass every raw column forward by default.
- **Dependency Inversion** — Gold depends on Silver's contract (its column names and grain), never reaches back into Bronze directly. If Bronze's raw shape changes, only Silver should need to change.

## Idempotency

Every notebook in this pipeline must be safely re-runnable — running it once or fifty times leaves the target table in the same state. Each spec states its strategy explicitly:
- **Full overwrite** — the default for anything cheap to fully re-derive (all of Bronze, most of Silver/Gold). Simpler and safer than incremental logic when the data volume doesn't demand it.
- **MERGE** — required wherever history must be preserved across runs (the SCD2 manager dimension) — overwrite would destroy it, plain append would duplicate it.

## Comments

Code comments in this repo are written for **any future reader** — a grader, a teammate, future-you, or an AI assistant with no memory of this project's history — not as personal shorthand. A comment explains **why** a non-obvious decision was made (a methodology choice, a workaround, a business rule), not what the line already says in plain sight.

## Spec template

Each spec follows this structure:
- **Purpose** — one or two sentences, business-oriented
- **Single Responsibility** — what this does, and explicitly what it does not do
- **Inputs** — source(s) and format
- **Outputs** — table name, grain, full column list
- **Transformation / business rules** — the actual logic, including non-obvious methodology decisions already made
- **Idempotency** — overwrite vs. merge, and why
- **Data quality checks** — what must be validated
- **Open questions** — anything genuinely still undecided

## Index

| Spec | Status |
|---|---|
| [01_bronze/ingest_index_prices](01_bronze/ingest_index_prices.md) | implemented |
| [01_bronze/discover_trust_universe](01_bronze/discover_trust_universe.md) | not yet built |
| [01_bronze/ingest_trust_prices](01_bronze/ingest_trust_prices.md) | not yet built |
| [02_silver/select_top20_trusts](02_silver/select_top20_trusts.md) | not yet built |
| [02_silver/clean_index_returns](02_silver/clean_index_returns.md) | not yet built |
| [02_silver/clean_trust_returns](02_silver/clean_trust_returns.md) | not yet built |
| [02_silver/load_manager_history](02_silver/load_manager_history.md) | not yet built |
| [02_silver/manager_history_research_playbook](02_silver/manager_history_research_playbook.md) | human process, in progress |
| [03_gold/build_dim_date](03_gold/build_dim_date.md) | not yet built |
| [03_gold/build_dim_financial_instrument](03_gold/build_dim_financial_instrument.md) | not yet built |
| [03_gold/build_dim_manager](03_gold/build_dim_manager.md) | not yet built |
| [03_gold/build_fact_monthly_performance](03_gold/build_fact_monthly_performance.md) | not yet built |
| [03_gold/build_fact_manager_tenure_performance](03_gold/build_fact_manager_tenure_performance.md) | not yet built |

Semantic-layer and orchestration specs aren't written yet — those components haven't been designed in enough detail to spec meaningfully; they'll be added once the view definitions and Workflow structure are decided.
