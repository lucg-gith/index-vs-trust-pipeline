# Do UK investment trusts beat the S&P 500?

A five-layer Databricks pipeline that measures the **beat rate**: the percentage of UK
investment trusts that outperformed the S&P 500 over a given window.

Not "which trust won" — the share that won. If 30 of 98 trusts beat the index over ten
years, the beat rate is 30%.

> **Status: in progress.** The pipeline is being built one layer at a time. Results below
> are filled in once Gold runs. Progress is tracked in [docs/PRD.md](docs/PRD.md) and in
> the repository issues.

## Reported twice, on purpose

The beat rate is reported at **four horizons — 15, 10, 5 and 3 years** — and **twice at
each horizon**: once including trusts that were delisted, once excluding them.

Funds that collapse stop being counted. Measure only the survivors and the industry looks
better than it was — **survivorship bias**. Most published comparisons disclaim it in a
footnote.

This project catches it happening. Of the 118 trusts in the universe, **Yahoo Finance
returns no data at all for 16** — ask it for `BCPT` or `CSH` and it answers
`No data found, symbol may be delisted`. The companies have been deleted from the source,
which is exactly how the bias is created. The pipeline records every one of those refusals
in `landing.yf_pull_log_raw` rather than letting them vanish.

Two of the deleted trusts survive in an archived CSV, so the beat rate can be computed with
and without them. **Two is a small cohort and the gap between the two numbers will be
small** — the point is the mechanism and the fact that the pipeline detects it, not a
precise estimate of the effect.

## Architecture

Catalog `index-vs-trust-pipeline` on Databricks Unity Catalog, five schemas:

| Layer | Job | Write mode |
|---|---|---|
| `landing` | data exactly as the source sent it — no transformation of any kind | OVERWRITE |
| `bronze` | same rows, every column STRING, nothing rejected | OVERWRITE |
| `silver` | all quality work — currency, stub rejection, total return | MERGE |
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
| Yahoo Finance via `yfinance` | **All prices, both sides.** Monthly bars, full history, with dividends. 100 of 118 trust tickers return data; 75 reach back 15 years or more, the oldest to 1967. SPY from 1993, plus IVV and VOO as a credibility check. SPLG is requested but Yahoo no longer serves it. |
| `data/uk_investment_trusts.csv` | Trust metadata — name, ticker, AIC sector, manager, management group. 120 rows, 118 tickers. Also defines the universe the Yahoo pull requests. |
| `data/uk_investment_trusts_price_history_monthly.csv` | An archive of the two delisted trusts Yahoo has erased, `BCPT` and `CSH`. Landed in full, but only those two are used. |

### How returns are measured

**Total return on both sides** — price movement plus dividends, compounded, computed with
one formula applied identically to the trusts and to SPY:

```
monthly return = (Close_t + Dividends_t) / Close_(t-1) − 1
```

This matters more than it sounds. UK investment trusts yield roughly 3–5% a year against
SPY's 1.3%, so comparing on price alone would hand the index a systematic head start of
several points a year and understate the beat rate.

**Yahoo's `Adj_Close` is deliberately not used.** It is dividend-adjusted for SPY, but for
UK trusts Yahoo records the dividend events and never applies them — 97 of 100 trusts show
an adjustment of under 0.5%. `HFEL` is the clearest case: 40 dividends totalling 232.6p
against a 359p starting price, yet an `Adj_Close` adjustment of 0.8%. Over ten years its
price return is **−25.8%** and its total return is **+39.0%**. Silver therefore builds
total return from `Close` and `Dividends` rather than trusting the adjusted column.

### Other things stated openly

- **No currency conversion.** Trusts are compared in GBp and SPY in USD, as percentage
  returns. Converting would import GBP/USD movement into a question about fund performance.
- Yahoo quotes 3 trusts in USD and 1 in EUR rather than GBp; Silver normalises the scale.
- 6 tickers return under 3 years of history and are rejected as stubs.

Every cleaning rule is backed by evidence in the EDA notebook rather than asserted.

## Repository layout

```
00_landing/     ingest notebooks and schema DDL
01_bronze/      all-STRING recast, plus the EDA that justifies Silver's rules
02_silver/      currency normalisation, stub rejection, total return
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
