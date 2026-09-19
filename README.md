# Do UK investment trusts beat the S&P 500?

A five-layer Databricks pipeline that measures the **beat rate**: the percentage of UK
investment trusts that outperformed the S&P 500 over a given window.

Not "which trust won" — the share that won. If 31 of 102 trusts beat the index over ten
years, the beat rate is 30%.

> **Status: in progress.** The pipeline is being built one layer at a time. Results below
> are filled in once Gold runs. Progress is tracked in [docs/PRD.md](docs/PRD.md) and in
> the repository issues.

## Reported twice, on purpose

The beat rate is reported at **four horizons — 15, 10, 5 and 3 years** — and **twice at
each horizon**: once including trusts that were delisted, once excluding them.

Funds that collapse stop being counted. Measure only the survivors and the industry looks
better than it was — **survivorship bias**. Most published comparisons disclaim it in a
footnote. Reporting both numbers turns the bias into a measured quantity: the gap between
the two *is* the bias, in percentage points.

## Architecture

Catalog `index-vs-trust-pipeline` on Databricks Unity Catalog, five schemas:

| Layer | Job | Write mode |
|---|---|---|
| `landing` | data exactly as the source sent it — no transformation of any kind | OVERWRITE |
| `bronze` | same rows, every column STRING, nothing rejected | OVERWRITE |
| `silver` | all quality work — month keys, scale repair, monthly returns | MERGE |
| `gold` | dimensional model, SCD Type 2 built via MERGE | MERGE |
| `semantic` | thin views feeding the dashboard | views |

Gold is a **star schema** — both dimensions join directly to both facts, nothing snowflaked:

```
dim_date  ──────────┐
                    ├──►  fact_monthly_performance
dim_ticker (SCD2) ──┤     fact_horizon_performance
                    ┘
```

`dim_ticker` holds the trusts *and* the index together, so comparing a trust to the S&P 500
is a self-join on one fact table rather than a union of two. It versions as SCD Type 2 when
a trust's manager, management group or listing status changes.

A diagram of the model is in [docs/star-schema.html](docs/star-schema.html).

## Data

| Source | What it gives |
|---|---|
| `data/uk_investment_trusts.csv` | Trust metadata — name, ticker, AIC sector, manager, management group. 120 rows, 118 tickers. |
| `data/uk_investment_trusts_price_history_monthly.csv` | Monthly prices, 16,357 rows across 102 tickers, 2011-09 to 2026-09. |
| Yahoo Finance via `yfinance` | The index side — SPY, with IVV/VOO/SPLG as a credibility check. |

### An honest caveat about returns

**Returns are price return on both sides.** The trust price history carries no dividend or
total-return column, so the only fair comparison is price against price — which means the
index side uses SPY's `Close`, never `Adj_Close`. Both sides are therefore understated by
roughly their dividend yield, and the beat rate is a price-return beat rate.

### Known defects in the source data, all handled in Silver

- Date labels mix month-end with next-month-first — 31 December can appear as 1 January.
- Around 25 tickers carry interleaved rows on the wrong scale, and the factor **drifts
  within a single ticker**, so no global correction exists.
- One zero price, and 145 sub-1.0 prices that are currency-quoted rather than wrong.

Every cleaning rule is backed by evidence in the EDA notebook rather than asserted.

## Repository layout

```
00_landing/     ingest notebooks and schema DDL
01_bronze/      all-STRING recast, plus the EDA that justifies Silver's rules
02_silver/      cleaning, scale repair, monthly returns
03_gold/        dimensions and facts
04_semantic/    views for the dashboard
data/           the committed source CSVs
docs/           the PRD and the star-schema diagram
```

## How to run

The `.ipynb` files are Databricks notebooks. Clone the repository into a Databricks Git folder
and run the layers in order — Landing, Bronze, Silver, Gold, Semantic — or attach them to a
single Workflow and run that. Every notebook ends with a verification cell whose expected
answer is known in advance.

## Results

To be filled in once Gold runs.

## Tech

Databricks, Unity Catalog, Delta Lake, Spark SQL, PySpark, `yfinance`, Databricks Workflows.
