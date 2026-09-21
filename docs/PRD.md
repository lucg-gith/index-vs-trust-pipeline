# PRD — Do UK investment trusts beat the S&P 500?

**Last updated:** 2026-09-21
**Current position:** **Step 8 of 9 — orchestration**, specced and awaiting approval:
`specs/05_orchestration/workflow.md`, one job of 21 tasks on a monthly schedule, sourced from
GitHub rather than the workspace. Revised 2026-09-20 to layer-first task names
(`bronze_ddl`, `gold_etl_dim_ticker`) with the notebooks renamed to match, and to a layer-gate
graph — each layer's DDL task is the gate into that layer. **Step 7 is complete:** the five semantic
views and the dashboard are both built and verified. The dashboard is a Databricks AI/BI page
created through the Lakeview REST API and published — one page, seven tiles, five datasets,
its definition version-controlled at `04_semantic/dashboard/beat_rate.lvdash.json`. A Power BI
build sheet in the same folder reproduces it by hand, because the Power BI REST API cannot
author report visuals. **Gold is complete and
the answer is in the warehouse:** only **5.3%** of
UK investment trusts beat the S&P 500 over 15 years, **10.6%** over 10 — and **none** beat it
over 15 or 10 years while also being less volatile. `gold.fact_horizon_performance` holds 445 rows across five horizons, with return, growth,
income, volatility, risk-adjusted return and three stored ranks. Growth — `price_return`,
dividends excluded — was added 2026-09-20 so the dashboard can show return and growth side by
side; the re-merge updated all 445 rows and inserted none. `gold.fact_monthly_performance`
holds 15,604 rows with zero orphan keys against either dimension. **Silver is verified** on Databricks as
of 2026-09-20: three notebooks ran green on the first attempt, 15,604 rows across 96
tickers, and every expected number matched bar one (see below). Landing, Bronze and EDA are
all verified too.

Writing the Silver spec re-derived the scale-repair evidence against the warehouse and
**overturned two EDA claims**: the corrupt prices are not clean powers of ten, and the true
cost of cleaning is 0.67% rather than 2.43%, because most bad rows are repairable from their
own high and low. It also added a new decision — Silver keeps only **2011-08 onward**, which
shrinks `dim_date` from ~710 rows to ~181. The price source changed on 2026-09-19 from the
CSV to Yahoo Finance, which adds dividends and history; Bronze was rebuilt the same week
against the new Landing.

---

## 1. The question

> **What percentage of UK investment trusts actually beat the S&P 500 — and did they
> take more risk to do it?**

Two instruments compared head to head: a **UK investment trust**, a listed fund where a
paid manager picks the holdings, against the **S&P 500** bought through SPY, which follows
a rule and charges almost nothing. The trust has to beat the index by enough to justify
both its fee and its risk.

**Return.** Not "which one won" — the **beat rate**: the share of trusts that outperformed
the index over a given window. If 30 of 98 trusts beat it over 10 years, the beat rate is
30%. Yield here means **total return** — price growth plus dividends, compounded — not
dividend yield.

**Risk.** Return alone flatters whoever took the most risk, so every horizon also carries
**annualised volatility** (`STDDEV(monthly_return) × √12` — how much the return bounces
around) and **risk-adjusted return** (annualised return ÷ volatility — reward per unit of
bounce). A trust that beat SPY by swinging twice as hard did not really beat it.
*Added 2026-09-20; max drawdown and hit rate were deliberately left out to keep scope down.*

Reported at **five horizons — 15, 10, 5, 3 and 1 years** — and **twice at each horizon**:
once including delisted trusts, once excluding them.

The full objective, including the four dashboard cuts, is in `specs/OBJECTIVE.md`.

### Why report it twice

Funds that collapse stop being counted. Measure only the survivors and the industry looks
better than it was — **survivorship bias**. Most published comparisons simply disclaim it.
Reporting both numbers turns the bias into a measured quantity: the gap between the two
*is* the bias, in percentage points.

**Reframed 2026-09-19, and this is the honest version.** The project demonstrates the
*mechanism* rather than sizing the effect. Two things support it:

- **Yahoo Finance has deleted 18 of the 118 trusts** in the universe. Ask it for `BCPT` or
  `CSH` and it answers `No data found, symbol may be delisted`. That deletion, recorded
  row by row in `landing.yf_pull_log_raw`, *is* survivorship bias happening in a live data
  source — not a caveat, but something the pipeline catches in the act.
- **Two of those trusts are recoverable** from the archived CSV, so the beat rate can still
  be computed with and without them.

Two trusts out of ~98 is a thin basis for a precise number, and the gap will be small. The
claim is therefore "here is how the bias is created and how a pipeline can detect it",
**not** "survivorship bias in UK trusts is N percentage points." Stating that limit plainly
is stronger than overclaiming from a sample of two.

This is still the project's main analytical contribution and the main thing to defend.

---

## 2. Success criteria

### The assignment

| Rubric level | Requirement | Status |
|---|---|---|
| **Minimum** | Bronze → Silver → Gold, at least 2 tables | on track |
| **Ideal** | plus MERGE, SCD Type 2, validations, automated workflow | on track — all four in scope |
| **Bonus** | plus dashboard, full documentation, video | dashboard and README in scope; video is step 9 |

### What "done" means here

1. The pipeline runs end-to-end, unattended, on a schedule.
2. Re-running it changes no row counts — **idempotent**.
3. Every cleaning rule traces to documented evidence in the EDA notebook.
4. Every number in the dashboard traces to a Gold table.
5. Every design decision has a one-sentence defence.

### Constraints shaping every decision

- **Defensible beats clever.** This is presented live in 5–10 minutes and questioned. A
  design that cannot be explained under pressure is worth less than a simpler one that can.
- **Time is the scarcest resource.** The brief says it outright: *"Don't try to do
  everything. A simple pipeline done well beats a complex one done halfway."*
- The employer is **never named** anywhere in the repo, commits or deliverables.

---

## 3. Scope

### In

- 96 UK investment trusts with usable monthly history from Yahoo, plus 2 delisted trusts
  recovered from the CSV archive. 75 of them reach back 15 years or more.
- The S&P 500 via SPY, with IVV/VOO as a secondary credibility check.
- **Total return on both sides** — price plus dividends, computed in Silver.
- Beat rate at 5 horizons times 2 survivorship treatments.
- **Risk as well as return** — annualised volatility and risk-adjusted return at every horizon, for trusts and index alike.
- SCD2 history on trust manager, management group and listing status.

### Out, and why

| Excluded | Reason |
|---|---|
| S&P 500 constituent-level modelling | SPY already publishes the index; modelling 500 stocks adds no answer |
| Currency conversion between GBP and USD | Both sides are measured as percentage returns in their own currency. Converting would import FX movement into a fund-performance question |
| Yahoo's `Adj_Close` | It is correct for SPY but not applied for UK trusts, so it cannot be used consistently. Silver builds total return from `Close` plus `Dividends` instead |
| A top-20 filter on the fact table | Filtering to the best performers before asking "what % beat the index" is circular |
| `rank_band` SCD2 | Existed only because no manager data was available. Manager history replaces it at a fraction of the complexity |
| `dim_manager` as a table | 224 of 227 managers run exactly one trust — the dimension would be a column in disguise, and it is many-to-many |

---

## 4. Data

**The price source changed on 2026-09-19.** Prices now come from Yahoo Finance for both
sides; the CSV that previously supplied them is kept only as an archive of trusts Yahoo has
deleted. Every fact below was verified against the live API or the files directly.

### Why the source changed

1. **The CSV has no dividends.** UK trusts yield roughly 3–5% a year and SPY about 1.3%, so
   comparing both on price alone hands the index a systematic several-point-a-year
   advantage and biases the beat rate downwards.
2. **The CSV history is shallow.** Every ticker in it starts 2011-09, barely covering the
   15-year horizon. Yahoo gives 75 trusts 15+ years and 10 more between 10 and 15.

### `data/uk_investment_trusts.csv` — metadata, and the universe

120 rows, 118 unique tickers. Trust name, ticker, AIC sector, **manager**,
**management_group**, notes. This is now the *only* use of this file, plus the ticker list
that drives the Yahoo pull.

- 227 distinct managers; **only 3 manage more than one trust**. 70 trusts have 2 or more
  managers (max 12).
- **52 management groups**, heavily shared — J.P. Morgan runs 12 trusts, Baillie Gifford 10.
- **It is a snapshot, not history.** No start/end dates. Run 1 makes everything version 1.

### Yahoo Finance via `yfinance` — all prices

Requested monthly, full available history, `auto_adjust=False, actions=True` so `Close`,
`Adj_Close`, `Dividends` and `Stock_Splits` all land. LSE tickers take a `.L` suffix.

**Trusts — 118 requested, verified 2026-09-19:**

| Outcome | Count |
|---|---|
| Usable series | **96** |
| Stub under 3 years, unusable | 4 — ADIG, BSIF, EOT, MNTN |
| No data at all | 16 |

The 16: `ABR ACI ADD AIS ASIT BCPT CDI CSH ECWO FJV PLI PRSR SCIN SSON THRB UKCM`.
Re-probed to rule out rate limiting; Yahoo's LSE coverage simply does not reach them.
Dividends are present for 90 of the 100 that return anything. Currencies are mixed:
**96 GBp, 3 USD, 1 EUR**.

**Index — SPY 405 monthly bars from 1993-01, IVV 317 from 2000-05, VOO 193 from 2010-09.
SPLG returns nothing.**

### `data/uk_investment_trusts_price_history_monthly.csv` — the delisted archive

16,357 rows, 102 tickers, 2011-09-30 to 2026-09-17, price only. Still landed in full, but
Silver takes **two tickers** from it: `BCPT` (158 rows to 2024-11) and `CSH` (112 rows to
2026-03). Yahoo has erased both, and they are the entire delisted cohort.

Four other tickers look delisted in this file but hold **one row each** — ADIG, BSIF, EOT,
MNTN. They are noise, not histories.

**Correction, 2026-09-20.** This file was described as the only dirty source. It is not.
EDA found the **mis-scaled rows and the `PCFT` zero are in the Yahoo data too** — the CSV
inherited them rather than introducing them. Only the mixed month-end date labels are
genuinely a CSV-only defect, and they are moot because Yahoo bars are all month-start.

### `landing.yf_pull_log_raw` — the pull log

One row per symbol requested, including the ones that returned nothing: 122 rows, 19 of
them `NODATA`. A refused symbol produces no price rows and would otherwise vanish without
trace. This table is the pipeline recording its own coverage gaps, and it is the evidence
behind the survivorship argument.

### Superseded

`trust_universe_seed.csv` — same 118 tickers, and its only extra column (`is_active`)
contradicted the price data. **Status is derived from Yahoo coverage plus the archive
instead.** Evidence beats assertion.

---

## 5. Architecture

Catalog `` `index-vs-trust-pipeline` `` — the hyphens mean **backticks on every SQL
reference**. Five schemas.

| Layer | Job | Write | Defends |
|---|---|---|---|
| **Landing** | data exactly as it arrived; no transformation at all | OVERWRITE | "what did the source actually send?" |
| **Bronze** | same rows, every column STRING, nothing rejected | OVERWRITE | one uniform contract for Silver |
| **Silver** | *all* quality work — scale repair, currency, total return | MERGE | "how do you handle bad data?" |
| **Gold** | dimensional model, SCD2 via MERGE | MERGE | "why this model?" |
| **Semantic** | thin views feeding the dashboard | views | keeps BI logic out of the model |

**No duplicates, guaranteed:** OVERWRITE into Landing and Bronze, MERGE on the business key
into Silver and Gold.

### Gold — a true star

Both dimensions join **directly** to both facts. Nothing is snowflaked.

```
dim_date  ──────────┐
                    ├──►  fact_monthly_performance
dim_ticker (SCD2) ──┤     fact_horizon_performance
                    ┘
```

- **`dim_ticker`** — trusts *and* SPY together, so trust-vs-index is a self-join on one
  fact rather than a union. `ticker_key = MD5(CONCAT_WS('|', ticker, effective_start_month))`.
  **A new version row opens when `manager`, `management_group` or `status` changes.**
  SPY never versions.
- **`dim_date`** — monthly, `month_key` a plain `YYYYMM` INT, not a hash: readable in
  output and sorts naturally. **Spans 2011-08 to the latest complete month (~181 rows)**,
  trimmed to the study window by Silver rule S3 — Yahoo reaches back to 1967-12, but the
  longest horizon is 15 years and the pre-2011 data is 12.4% corrupt against 0.67% inside
  the window. *Revised 2026-09-20; it briefly read ~710 rows from 1967-12.*
- **`fact_monthly_performance`** — one row per (ticker, month). Carries the **versioned**
  `ticker_key`, resolved once at build time, so "returns while managed by X" is a plain
  join with no date-range condition to forget.
- **`fact_horizon_performance`** — one row per (ticker, horizon), 5 horizons. `total_return`,
  `annualised_return`, `index_return_same_period`, `beat_index`, and the risk pair added
  2026-09-20: `volatility`, `index_volatility_same_period`, `risk_adjusted_return`.

### Why the SCD2 is on the manager

The manager file is a snapshot, so on run 1 every trust is version 1 and history accrues
from run 2. That is normal, and it makes for a **live demo**: change one manager in the
CSV, re-run, `SELECT * WHERE ticker = 'X'` — two rows on screen, 30 seconds.

---

## 6. How each step is run

Five phases, every step, in order:

**plan → agreement (spec file) → build → implement → verify**

The spec file is the agreement artifact: written, presented, and explicitly approved
*before* the code for that step exists. One step at a time, review between each.

Specs live in `specs/<layer>/` and are gitignored — working notes, not deliverables.

---

## 7. Build plan and progress

✅ done · 🔵 in progress · ⬜ not started · ⏸️ parked

| # | Step | Plan | Spec | Agreed | Built | Verified |
|---|---|:--:|:--:|:--:|:--:|:--:|
| 0 | **Design** — close the design tree | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1 | **Landing** — 4 ingests plus schema | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4b | **Silver revision** — repair the half-applied splits | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | **EDA** — evidence for Silver's rules | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | **Silver** — scale repair, currency, total return | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4b | **Silver revision** — repair the half-applied splits | ✅ | ✅ | ✅ | ✅ | ⬜ |
| 5 | **Gold dims** — `dim_date`, `dim_ticker` SCD2 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | **Gold facts** — monthly plus horizon, return + risk | ✅ | ✅ | ✅ | ✅ | ✅ |
| 7a | **Semantic** — five thin views over Gold | ✅ | ✅ | ✅ | ✅ | ✅ |
| 7b | **Dashboard** — one page, seven tiles | ✅ | ✅ | ✅ | ✅ | ✅ |
| 8 | **Orchestration** — one monthly Workflow | ✅ | ✅ | ✅ | ✅ | ⬜ |
| 9 | **Presentation** — README, video, LinkedIn | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

### Open at this moment

- **Silver spec approved 2026-09-20, notebooks built** — `specs/02_silver/silver.md`,
  eleven rules closing all eight items EDA left open. Two things in it are new rather than
  merely chosen. First, the scale-repair rule is now **evidence-led rather than
  threshold-led**: a `Close` outside its own bar's `High`–`Low` is impossible, so those rows
  are provably corrupt *and* repairable from the same row, and the repair is validated
  out-of-sample against the next month's `Open` (2.17% error, against 447% uncorrected).
  295 repaired, 107 deleted, 0.67% of the study window lost. Second, **Silver keeps only
  2011-08 onward**, because nothing older is read by any metric and the pre-2011 data is
  12.4% corrupt against 0.67% inside the window — this shrinks `dim_date` from ~710 rows to
  ~181 and is a change to a previously agreed design point.
- **Silver is verified.** `silver.monthly_performance` holds **15,604 rows across 96
  tickers**, `silver.ticker` holds **121**, and `silver.price_repair_log` holds **346** —
  252 repaired, 94 deleted. Both integrity checks return **0**: no non-positive close, and
  nothing left more than 2x from its neighbourhood median. `PCFT` 2019-11 came back as
  141.25 from a recorded 0.0, `JEMA` 2022-12 as 84.877 from 42.87, and `CSH`'s maximum close
  fell from 112.8 to 2.945.
- **Testing the built pipeline found two more defects, both now fixed (S2d, S2e).** First,
  the mid-point repair could be taken from a bar whose `High` and `Low` are in different
  units — `WWH` 2012-01 reads `H=773.00 L=72.50` — overwriting closes that were already
  correct. A bar is now only used when `High <= 2 * Low`. Second, **five trusts cross a split
  back-adjustment that Yahoo only half applied** (`MRC`, `MYI`, `NAS`, `PCT`, `WWH`), and a
  sixth (`JEMA`) still held an impossible month after every repair: their
  early months are in the pre-split unit and later months in the post-split one. Rescaling
  was tried and failed, so they are excluded whole and named. Left in, `WWH` reported a
  15-year return of **−50.9%** against a truthful figure near **+356%**. They are detected by
  requiring the level to step by the trust's **own recorded split ratio**, which leaves a
  genuine collapse like `CHRY` in 2022 untouched.
- **Cross-validation that the return maths is right:** SPY, IVV and VOO independently give
  10-year price returns of 252.9 / 252.5 / 253.3% against the documented +252%, and SPY's
  15-year annualised volatility is **14.3%**, the textbook figure for the S&P 500.
- **A documentation error was found and corrected:** HFEL's old "+39.0% total return" did not
  reinvest dividends while the SPY "+312%" it was paired with did. The pipeline compounds
  both sides identically and gives HFEL **+74.7%**.
- **The job was submitted twice and returned identical counts** — now **15,604 / 121 / 346** — with row counts equal to distinct business keys in every table. Delta history proves it directly: run 1 of the split repair reported **88 inserted, 15,516 updated**, and run 2 reported **0 inserted, 15,604 updated, 0 deleted** in both Silver and Gold, with `fact_horizon_performance` at **0 inserted, 445 updated** both times. That is the MERGE doing its job, and the answer to "how do you guarantee no duplicates?"
- **One prediction was wrong and the data was right:** distinct `management_group` is **53**,
  not 52, because 19 trusts carry an empty string rather than a null. The 52 real groups are
  intact. Whether to normalise `''` to null is **open for Gold**, where the column is used.
- **Rule S2b was added during the build**, because the spec's own verification cell failed on
  its first dry run. It found `JEMA` 2022-12 — `low 79.75, high 90.00, close 42.87` — corrupt
  but off by almost exactly 2x, so the neighbourhood test let it through. Detecting a close
  that also sits more than 25% outside **its own bar** catches 89 more rows across 17 trusts.
  Compounded returns are unchanged to one decimal place on all 16 affected trusts, because a
  corrupt month cancels itself; **volatility was overstated by up to 2.4x** (`PIN` 89.2% vs
  36.7%, `CLDN` 44.6% vs 19.0%). Since the objective now asks about risk as well as return,
  that is the difference between answering the question and answering it wrongly.
- **Two EDA claims were disproved** in the process and corrected in `specs/01_bronze/eda.md`:
  the corrupt prices are not clean powers of ten, and cleaning costs 0.67%, not 2.43%.
- The user asked for **both price return and total return** on every row, so the dividend-less
  archive trusts (`BCPT`, `CSH`) can be judged against SPY's *price* return rather than its
  total return. We never compare a price return to a total return.
- **Objective extended 2026-09-20.** The question now has a **risk** half as well as a return
  half — volatility and risk-adjusted return at every horizon — and a **1-year** horizon was
  added, making five. Dashboard scope was un-parked at the same time. Nothing built so far is
  affected: Landing, Bronze, EDA and the whole Silver plan stand unchanged, because the risk
  metrics are aggregates over the monthly return series Silver already produces. Settled in
  `specs/OBJECTIVE.md`.
- **Landing and Bronze are both verified.** Landing ran 2026-09-20 as a five-task chained job, all
  SUCCESS. Landed: 120 metadata rows, 16,357 CSV archive rows, 35,121 Yahoo trust rows
  across 100 symbols, 915 index rows across 3, and 122 pull-log rows. Two spec numbers were
  wrong and are corrected: `APAX` and `HET` return an empty frame rather than data, so it is
  100 OK / 18 NODATA, not 102 / 16; and `yfinance` reaches far deeper than the chart API
  suggested, back to **1967-12**, so the trust table is 35,121 rows rather than ~24,600.
  The design conclusions are unchanged — 96 usable trusts, depth split 75 / 10 / 10 / 1.
  A second full run returned identical counts, including the pull log holding at 122 rather
  than doubling, which proves the delete-then-append slice logic.
- **Bronze ran green on its first attempt**, six tasks fanning out from the schema task.
  Row parity with Landing on all five tables, every column STRING, and the checks that
  matter by *not* changing: `PCFT` still `0.000`, 2 blank tickers intact, 19 NODATA rows
  intact, `Capital_Gains` present on the index table and absent on the trust table.
- **EDA ran green on all five notebooks.** Three predictions matched exactly (horizon
  ceilings 75 / 85 / 95 / 96, the pull log reconciling 100 of 100 against the price rows,
  and 97 of 100 priced trusts having a manager). One did not: **`CSH` mixes pounds and
  pence** — 10 of its 112 months sit near 105 while the rest sit near 1.05. That is half
  the delisted cohort, so Silver has to fix it before the survivorship number means
  anything. Recorded as finding 2.3b.
- **The old Bronze was deleted and rebuilt** on 2026-09-19/20, because all four notebooks
  targeted Landing tables that had been renamed or replaced. The agreement it was built
  under is kept as `specs/01_bronze/bronze-superseded-2026-09-18.md`.
- **The Databricks Git folder was re-cloned on 2026-09-20.** Its old copy had truncated
  markdown cells and uncommitted run outputs, which blocked the pull; a clean clone fixed
  both. It now tracks `main`.

### Step detail
**Step 3 — EDA** *(next)*
Five notebooks, one per Bronze table, producing the documented evidence behind every Silver
rule. Spec in `specs/01_bronze/eda.md`. Read-only, not part of the scheduled Workflow.
The headline finding is already in: the mis-scaled price rows are **in the Yahoo source**,
affecting 36 of the 96 usable trusts inside the 15-year window, which reinstates the scale
repair that the Landing spec had retired.

**Step 4 — Silver** *(spec approved and built 2026-09-20; three notebooks, verifying)*
Eleven rules (S1–S11), each citing the EDA finding it answers. Three tables: `silver.ticker`
(121 rows), `silver.monthly_performance` (15,604 rows) and `silver.price_repair_log` (346
rows, the audit trail for every value changed or removed).

The hard rule is **S2, scale repair**: detect a close that is zero or more than 2x from the
median of its 13-month neighbourhood, repair it to that bar's own `(High + Low) / 2`, re-test
the repair, and delete the month if it still fails. **252 repaired, 88 split-repaired, 6 deleted** out of
15,604 — 2.2%. It is verified out-of-sample against the next month's opening price (2.17%
error repaired, against 447% uncorrected and 0.47% for a clean row), and proved to be
catching data defects rather than volatility by firing **zero** times in March 2020 while
firing 24 times in each of two calm months. It also subsumes the `PCFT` zero with no special
case. Two EDA claims were overturned in the process and corrected there.

The other rules: the month key (`YYYYMM` INT, with the `day <= 3` variant for the CSV
archive), **S3 the 2011-08 study window**, partial-month exclusion derived from the pull log,
**both `price_return` and `total_return` on every row** so the dividend-less archive trusts
are compared against SPY's price return rather than its total return, currency carried but
never converted (a return is unit-free), stubs kept for Gold to filter, null managers carried,
status derived, MERGE on the business key.

S3 is a change to a previously agreed design point — see `dim_date` above.

**Step 4b — Silver revision: the half-applied splits** *(complete and verified 2026-09-21)*
Yahoo left four quarter-end months — 2011-12, 2012-03, 2012-06, 2012-09 — on the pre-split
scale for 22 trusts, so Silver correctly refuses to repair the bar and deletes the month,
costing 8 monthly returns each. One extra repair candidate, `close / F` where `F` is the
product of the splits Yahoo itself reports after that month, rescues **88 of the 94 deleted
rows**. Simulated read-only against Bronze on 2026-09-21: `fact_monthly_performance` goes
**15,516 → 15,604**, the study stays at **96** tickers and `fact_horizon_performance` at
**445**, and the CSV archive — an independent provider corrupted in *different* months —
agrees with **87 of the 88** repaired prices and with **none** of the originals. Spec in
`specs/02_silver/split-repair.md`, closed as issue #14. **Run 2026-09-21, all seven tasks green.** The beat rates did not move at all — 5.3 / 10.6 / 15.6 / 30.0 / 41.6 — because eight restored months changed returns without flipping a verdict. What moved: ATT from 24.9% a year to 22.9%, out-yielding from 40 of 76 to 41, and 15-year median volatility 24.2% to 24.0%. Re-measured in
every published figure.

**Step 5 — Gold dimensions** *(next)*
`dim_date` (~181 rows, 2011-08 onward) and `dim_ticker` with the SCD2 MERGE closing and
opening version rows.

**Step 6 — Gold facts**
`fact_monthly_performance`, then `fact_horizon_performance` at **five horizons** with the
36-month minimum, delisted trusts judged over their own lifespan against the index over that
same span, and **volatility plus risk-adjusted return** aggregated over each window.

**Step 7 — Semantic and dashboard** *(done)*
Five thin views over Gold, then one AI/BI dashboard page over two of them. Dashboard scope was
cut from four pages to seven tiles on 2026-09-20: three counters (return, growth, income),
beat rate by horizon, beat rate by management group, the survivorship pair, and a top-20 table
naming the managers with the index ranked into it.
Three counters, one per question: over 15 years 5.3% beat the index on total return, 5.3%
out-grew it on price alone, and 53.9% paid more income than it. At 5 years the first two split
— 15.6% against 8.9% — which is the dividends doing the work. **Volatility was removed from the
dashboard on 2026-09-20** after three attempts at charting it; it stays computed in Gold, so
the honest line is "I measured it and kept the page focused", not "I did not look at risk".
Each tile owns its own dataset, so no click can recompute another tile. The three cuts by
management group, manager structure and AIC sector stay as `v_beat_rate_by_cut` and are quoted
aloud rather than drawn. Full detail in `specs/04_semantic/dashboard.md`.

**Step 8 — Orchestration**
One Databricks Workflow, chained tasks, monthly schedule. Not theatre: the SPY side
genuinely gains a month per run. Tasks are named `<layer>_<ddl|etl>[_<object>]` and the
notebooks are renamed to match, so a task box's title and its file path read the same. Each
layer's DDL task gates the layer, so the board reads as five columns.

**Step 9 — Presentation**
README (architecture diagram, how to run, results), 5–10 minute video, LinkedIn post.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| **yfinance is now a single point of failure.** It is an unofficial scraper and both sides of the comparison depend on it | The biggest risk in the project since 2026-09-19. Landing OVERWRITEs per run, so a bad pull replaces a good one. Mitigation: the pull log makes a degraded run obvious at a glance, and the verification cells assert exact symbol counts rather than "it ran" |
| **The scale repair is the hardest piece.** 36 of 96 trusts carry mis-scaled rows inside the window, 743 in total, and the factor differs by ticker — CGT a clean 10x, CLDN roughly 1400x | Detect per row against the median of neighbouring months, derive the ratio, rescale. Step 3 must prove the detection works before step 4 relies on it. Excluding the affected trusts instead would discard 37% of the sample |
| **The total-return calculation is the number everything rests on** | One formula, applied identically to trusts and SPY so any error cancels on both sides. Re-measured from `gold.fact_horizon_performance` 2026-09-21: HFEL over 10 years, price return **−22.9%** against total return **+74.7%**. *The older +39.0% figure did not reinvest the dividends while the SPY figure it was paired with did — an apples-to-oranges the pipeline does not repeat.* |
| **Survivorship rests on 2 trusts** | Reframed: the claim is the mechanism, evidenced by Yahoo's 16 deletions, not a precise effect size. Stated as a limitation in the README rather than buried |
| **SCD2 has no history on run 1** — the source is a snapshot | Expected and explained. Demo it live by changing a manager and re-running |
| Time runs out before step 9 | Steps 1–6 clear "Ideal" on their own. Dashboard and video are bonus — cut from the end, not the middle |
| Trusts with no manager in the metadata | They stay in `dim_ticker` with a null manager. Not dropped — the universe stays honest |

---

## 9. Deliverables checklist

- [ ] Pipeline running end-to-end on a schedule
- [ ] README: one-line what, architecture diagram, tech list, how to run, results
- [ ] Dashboard screenshots
- [ ] 5–10 minute video with voice
- [ ] LinkedIn post linking repo and video
- [ ] **Stated openly in the README:** returns are **total return** on both sides, built in
      Silver from `Close` plus `Dividends`, because Yahoo's `Adj_Close` applies dividends
      for SPY but not for UK trusts
- [ ] **Also stated openly:** the delisted cohort is 2 trusts, so the survivorship figure
      illustrates the mechanism rather than sizing the effect
- [ ] **Also stated openly:** returns are compared in each side's own currency, with no
      GBP/USD conversion

---

## 10. Defence — one sentence each

| Question | Answer |
|---|---|
| Why this dimensional model? | One fact, two dims, every dim joins straight to the fact. Trust vs index is a self-join on one table. |
| How do you guarantee no duplicates? | OVERWRITE into Landing and Bronze, MERGE on the business key into Silver and Gold. |
| Show me your SCD2 | A trust's manager, firm or listing status changes and I close the old row and open a new one — watch, I'll change one and re-run. |
| What if the source changes schema? | Bronze casts every column it finds to STRING, so nothing is ever dropped — a new column just lands and waits. Silver names the columns it needs, so a missing one fails there, at the point where it actually matters. |
| Why is there a Landing *and* a Bronze? | Landing is a transient receiving zone holding exactly what arrived; Bronze is the permanent record under one all-STRING contract. |
| Why no lineage columns? | Delta's `DESCRIBE HISTORY` already records load time, user and notebook, and UC draws lineage. With OVERWRITE, a per-row stamp would repeat one value across every row. |
| Why total return and not just price? | UK trusts yield 3–5% a year against SPY's 1.3%, so price-only comparison silently favours the index. I compute both sides the same way from `Close` plus `Dividends`. |
| Why measure volatility too? | A trust that beats the index by swinging twice as hard has not beaten it in any way an investor would accept. Volatility is the standard deviation of monthly returns, annualised; dividing return by it gives reward per unit of risk. Same window, two more aggregates. |
| Why not max drawdown or a Sharpe ratio? | Drawdown is a good number and I would add it next. Sharpe needs a risk-free rate, which is a whole extra source for one ratio. I kept the two measures that answer the question and left the rest out on purpose. |
| Why a 1-year horizon as well? | It costs one row per trust and gives the recent picture to contrast against the 15-year one. Three years stays as the floor because 36 months is the minimum history to enter the facts at all. |
| Why not use Yahoo's `Adj_Close`? | It is dividend-adjusted for SPY but not for UK trusts — 97 of 102 show an adjustment under 0.5%, including HFEL, which paid 237.7p of dividends on a share that started the window at 343p. Using it would understate the trusts. |
| How do you know delisted trusts are missing? | The pipeline records it. `landing.yf_pull_log_raw` holds a row per requested symbol, and 18 trusts return nothing — 16 with `No data found, symbol may be delisted`, 2 with an empty frame. |
| What would you do with more time? | Source real manager history so the SCD2 has depth on day one, and find a source for the delisted trusts so survivorship rests on more than two. |
