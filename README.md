# Do UK investment trusts beat the S&P 500?

## Description and Objectives

This project builds an end-to-end data pipeline on Databricks to answer a question a
private investor can act on: **what percentage of UK investment trusts actually beat the
S&P 500 — and did they take more risk to do it?**

A **UK investment trust** is a listed company on the London Stock Exchange whose business
is holding shares in other companies, picked by a paid manager. The **S&P 500**, bought
through the SPY tracker, follows a rule and charges almost nothing. The trust has to beat
the index by enough to justify both its fee and its risk.

The headline measure is the **beat rate** — not "which trust won", but the *share* that
won. If 9 of 85 trusts beat the index over ten years, the beat rate is 10.6%.

Three objectives shape the design:

1. **Measure return honestly.** Total return on both sides — price movement plus dividends
   reinvested — so the comparison is not quietly rigged by the trusts' higher yield.
2. **Measure the risk taken to get it.** Annualised volatility and risk-adjusted return at
   every horizon, because return alone flatters whoever gambled hardest.
3. **Turn survivorship bias into a measured number.** Every figure is reported **twice per
   horizon** — once including delisted trusts, once excluding them — so the bias is a
   quantity in the output rather than a caveat in a footnote.

Results are reported at **five horizons: 15, 10, 5, 3 and 1 years**, and surfaced through
an interactive Databricks AI/BI dashboard.

### Why report every number twice

Funds that collapse stop being counted. Measure only the survivors and the industry looks
better than it was — this is **survivorship bias**.

This pipeline catches it happening in the source. Of the 118 trusts in the universe,
**Yahoo Finance returns no data at all for 18** — ask it for `BCPT` or `CSH` and it answers
`No data found, symbol may be delisted`. The companies have been erased from the source,
which is exactly how the bias is created. Every one of those refusals is recorded as a row
in `landing.yf_pull_log_raw` rather than being allowed to vanish.

Two of the erased trusts survive in an archived CSV, so the beat rate can be computed with
and without them. **Two is a thin cohort and the measured gap is at most one percentage
point** — so the claim made here is "this is how the bias is created and how a pipeline can
detect it", not "survivorship bias in UK trusts is N points".

## Results

Measured from `gold.fact_horizon_performance` on 2026-09-21.

| Horizon | Trusts | **Beat the S&P 500** | Median trust volatility | SPY volatility | **Beat it *and* were calmer** |
|---|---|---|---|---|---|
| **15 years** | 76 | **5.3%** — 4 trusts | 24.0% | 14.2% | **0.0%** |
| **10 years** | 85 | **10.6%** — 9 trusts | 25.4% | 15.3% | **0.0%** |
| 5 years | 90 | 15.6% | 26.7% | 15.9% | 1.1% |
| 3 years | 90 | 30.0% | 27.1% | 12.9% | 0.0% |
| 1 year | 89 | 41.6% | 23.1% | 13.2% | 4.5% |

Over fifteen years, four trusts out of seventy-six beat the index — and **not one** of them
did it while also being less volatile than it. The typical trust swung around about 70%
harder than the index. The shorter the window, the better active management looks.

**The fair counterweight.** Over the same fifteen years, 4 of 76 trusts beat the index on
total return, but **41 of 76 — 53.9% — paid more income than it did**. The two instruments
are built for different jobs, and the dashboard shows both counters side by side.

**Survivorship.** Including or excluding the delisted cohort moves the beat rate by at most
1.0 percentage point, and it moves in both directions — a demonstrated mechanism, not a
measured effect size.

## Architecture

Catalog `index-vs-trust-pipeline` on Databricks Unity Catalog. Five layers, each with one
job and one write mode:

| Layer | Job | Write mode |
|---|---|---|
| **`landing`** | Ingestion of raw data exactly as the source sent it — from the `yfinance` API and from CSVs in Databricks Volumes. No transformation of any kind. | OVERWRITE |
| **`bronze`** | The same rows, every column typed STRING. Nothing validated, nothing rejected. | OVERWRITE |
| **`silver`** | All quality work: scale repair, stock-split repair, currency handling and the total-return calculation. | MERGE |
| **`gold`** | The dimensional model — a star schema with SCD Type 2 maintained by MERGE. | MERGE |
| **`semantic`** | Thin views feeding the dashboard, so no visual contains business logic. | views |

The split between Bronze and Silver is deliberate: Bronze preserves the evidence that a
value was broken, Silver holds the repair, and every repair is logged row by row in
`silver.price_repair_log` so any cleaned number can be traced back to what it was.

## Technologies

- **Processing engine:** Databricks / Apache Spark
- **Languages:** SQL (Spark SQL) for all transformations, PySpark only for API ingestion
- **Storage:** Delta Lake and Databricks Volumes, governed by Unity Catalog
- **Orchestration:** Databricks Workflows — monthly schedule under the rule
  **1 notebook = 1 task**, sourced directly from GitHub
- **Ingestion:** `yfinance` (Yahoo Finance API)
- **Visualisation:** Databricks AI/BI (Lakeview), plus a Power BI rebuild sheet
- **Version control:** Git / GitHub

The transformations lean on SQL window functions rather than DataFrame chains: `LAG` for
month-on-month total return, `FIRST_VALUE`/`LAST_VALUE` for horizon returns, `LEAD` for
closing SCD Type 2 versions, and `RANK` over `PARTITION BY` for the leaderboards.

## Data Modeling

The Gold layer is a **true star schema** — both dimensions join **directly** to both facts,
with nothing snowflaked:

```
dim_date  ──────────┐
                    ├──►  fact_monthly_performance   (ticker, month)
dim_ticker (SCD2) ──┤            │
                    ┘            └──►  fact_horizon_performance   (ticker, horizon)
                                        ▲          ▲
                    both dimensions join this fact directly too
```

The two facts sit at different grains, and the second is **derived from the first**:
`fact_horizon_performance` is built from `fact_monthly_performance`, not from Silver alongside
it. The aggregate is computed from the detail it aggregates, so the two cannot drift apart.

**Fact tables:**

- **`fact_monthly_performance`** — grain: one row per ticker per month. 15,604 rows.
  Carries `close`, `dividend`, `price_return` and `total_return`, plus the *versioned*
  `ticker_key`.
- **`fact_horizon_performance`** — grain: one row per ticker per horizon. 445 rows across
  the five horizons. Carries `total_return`, `annualised_return`, `income_return`,
  `volatility` and `risk_adjusted_return`, the matching index figures for the same period,
  the `beat_index` flag, and three stored ranks.

**Dimension tables:**

- **`dim_ticker`** (**SCD Type 2**) — 121 rows holding the trusts *and* the index together,
  with `manager`, `management_group`, `aic_sector`, `currency` and `status`. A new version
  opens when **manager**, **management group** or **listing status** changes, dated by
  `effective_start_month` / `effective_end_month` with an `is_current` flag. The surrogate
  key is `MD5(CONCAT_WS('|', ticker, effective_start_month))`.
- **`dim_date`** — monthly grain, 181 rows covering 2011-08 to 2026-08. `month_key` is a
  plain `YYYYMM` integer, deliberately not a hash, so a fact row stays readable without a
  join.

Holding the index inside `dim_ticker` alongside the trusts is what makes the star work:
comparing a trust to the S&P 500 becomes a self-join on one fact table instead of a union
of two.

`dim_manager`, `dim_management_group` and a degenerate rank dimension were each considered
and rejected — manager and group are attributes of a ticker that change over time, which is
precisely what SCD Type 2 already handles.

## Analytical Dashboard

One Databricks AI/BI page, seven tiles, built on five semantic views and version-controlled
as `dashboard/beat_rate.lvdash.json`.

**KPIs:**

- **Beat rate** — the share of trusts above the index, on return, growth or income.
- **Risk-adjusted verdict** — the share that beat the index *and* were less volatile than it.
- **Index rank** — where the S&P 500 itself places in the field, always on screen.
- **Survivorship gap** — the beat rate including and excluding delisted trusts, side by side.

**Visualisations:**

- **Counter row:** return, growth and income read left to right — the fairness argument in
  three numbers.
- **Beat rate by horizon:** one bar per horizon, showing how much better active management
  looks the shorter the window.
- **Risk/return scatter:** every trust plotted against the index, so the "won by taking more
  risk" quadrant is visible rather than asserted.
- **Management group chart:** beat rate by house, with the trust count printed beside each
  name, so a rate is never read without its sample size.
- **Top 20 leaderboard:** the best trusts on the selected measure, with manager and group
  named, and the index ranked in among them.

Two filters drive the page: the **horizon** (15/10/5/3/1 years) and the **measure** to
compare on.

## Data Sources

| Source | What it provides |
|---|---|
| **Yahoo Finance**, via the `yfinance` API | **All prices, both sides.** Monthly bars with dividends, requested with `auto_adjust=False, actions=True`. 122 tickers requested: 103 returned data, 19 returned nothing. SPY from 1993, with IVV and VOO pulled as a credibility check. |
| **`data/uk_investment_trusts.csv`** | Trust metadata — name, ticker, AIC sector, manager, management group. 120 rows, 118 tickers. Also **defines the universe** the Yahoo pull requests. |
| **`data/uk_investment_trusts_price_history_monthly.csv`** | An archive of delisted trusts Yahoo has erased. Landed in full (16,357 rows), but only `BCPT` and `CSH` are used — the two with enough history to produce a return. |

After cleaning, the warehouse holds **96 tickers** with usable monthly history: 90 active
trusts, 3 delisted trusts, and the 3 index trackers.

### How returns are measured

**Total return on both sides** — one formula applied identically to the trusts and to SPY:

```
monthly return = (Close_t + Dividends_t) / Close_(t-1) − 1
```

This matters more than it sounds. UK investment trusts yield roughly 3–5% a year against
SPY's 1.3%, so comparing on price alone would hand the index a systematic head start of
several points a year and understate the beat rate.

**Both sides are already net of costs, so no fee column is needed.** A trust's ongoing
charges are deducted from its own assets, which reduces its net asset value and feeds
through to its share price; SPY's expense ratio works the same way. Subtracting a fee on
top would double-count it. The gap in those charges is wide — UK trusts typically run
0.4–2% a year against roughly 0.09% for SPY — so the beat rate compares what an investor
actually keeps *after* paying for active management.

**Yahoo's `Adj_Close` is deliberately not used.** It is dividend-adjusted for SPY, but for
the UK trusts Yahoo records the dividend events and never applies them — 97 of 100 trusts
show an adjustment of under 0.5%. `HFEL` is the clearest case: 40 dividends totalling 232.6p
against a 359p starting price, yet an `Adj_Close` adjustment of 0.8%. Over ten years its
price return is **−22.9%** and its total return is **+74.7%**. Silver therefore builds total
return from `Close` and `Dividends` rather than trusting the adjusted column.

### Limitations, stated up front

- **No currency conversion.** Trusts are compared in GBp and SPY in USD, as percentage
  returns. Converting would import GBP/USD movement into a question about fund performance.
- **The delisted cohort is two trusts**, so survivorship demonstrates the mechanism rather
  than sizing the effect.
- **These are share-price returns, not NAV returns.** Investment trusts are closed-ended, so
  their shares trade at a discount or premium to net asset value, and that movement forms
  part of the measured return. This is deliberate — the share price is what an investor
  actually receives — but a trust's figure therefore reflects both its manager and its
  rating. SPY, being an ETF, tracks its NAV closely, so the effect is one-sided.
- **The universe is a subset.** The AIC represents roughly 350 closed-ended companies; this
  study covers 118 of them, spanning 36 AIC sectors. Any skew is likely to favour large,
  well-known survivors — which would make the low beat rate conservative rather than
  inflated.
- **Income is cumulative over the window, not an annual yield** — the index's 69.3% at
  fifteen years is dividends over fifteen years as a share of what you paid.
- Yahoo quotes 3 trusts in USD and 1 in EUR rather than GBp; Silver normalises the scale.

Every cleaning rule is backed by evidence in the EDA notebooks rather than asserted.

## Repository Structure

The repository is organised by **what a thing is** — a declaration you run once, or a load
that runs every month — rather than by which layer it belongs to.

```
ddl/            declares the catalog — run once, not on any schedule
  ddl_schemas.ipynb                    the five schemas, one notebook
  00_landing/ 01_bronze/ 02_silver/    one notebook per table
  03_gold/ 04_semantic/                one notebook per table or view

etl/            the monthly pipeline — this is what the Workflow runs
  00_landing/ 01_bronze/ 02_silver/    one notebook per load
  03_gold/                             (semantic has no ETL: a view is its own definition)

eda/            systematic profiling that justifies each of Silver's cleaning rules
dashboard/      the Lakeview dashboard definition, plus a Power BI rebuild sheet
orchestration/  two job definitions — workflow.json (monthly) and setup.json (once)
data/           the committed source CSVs
docs/           the PRD and the star-schema diagram
```

`CREATE TABLE` is deployment, not pipeline. The DDL runs once from its own unscheduled job;
the monthly job is **15 ETL tasks and nothing else**, because re-running
`CREATE TABLE IF NOT EXISTS` every month is work that can only ever do nothing.

Every notebook is named `<layer>_<ddl|etl>[_<object>]` — `bronze_ddl_trusts`,
`gold_etl_dim_ticker` — and that name is also its Workflow task key, so a box on the job
graph and a file in the repository carry the same name, and there is one string to search
for.

## How to Run

The `.ipynb` files are Databricks notebooks. Clone the repository into a Databricks Git
folder, then:

1. **Once** — run the job defined in `orchestration/setup.json`. It creates the five
   schemas, then every table and view. Nothing here runs again.
2. **Every month** — the job defined in `orchestration/workflow.json` runs on its own
   schedule, on the 2nd at 06:00 Europe/London. It can also be triggered by hand.

The pipeline is **idempotent**: re-running it changes no row counts. Every notebook ends
with a verification cell whose expected answer is stated in advance, and the monthly load
refuses to overwrite good data with a degraded API pull.

A diagram of the dimensional model is in [docs/star-schema.html](docs/star-schema.html), and
the full build plan and progress tracker is in [docs/PRD.md](docs/PRD.md).
