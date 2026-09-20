# PRD — Do UK investment trusts beat the S&P 500?

**Last updated:** 2026-09-20
**Current position:** Step 4 of 9 — Silver. **Landing, Bronze and EDA are all verified** on
Databricks as of 2026-09-20. EDA found that the mis-scaled rows come from Yahoo, not the
CSV, which reinstated the scale repair. The price
source changed on 2026-09-19 from the CSV to Yahoo Finance, which adds dividends and history
back to 1967. Bronze was deleted the same day and rebuilt on 2026-09-20 against the new
Landing: six notebooks, each casting the live schema to STRING rather than naming columns.

---

## 1. The question

> **What percentage of UK investment trusts actually beat the S&P 500?**

Not "which one won" — the **beat rate**: the share of trusts that outperformed the index
over a given window. If 30 of 98 trusts beat it over 10 years, the beat rate is 30%.

Reported at **four horizons — 15, 10, 5 and 3 years** — and **twice at each horizon**:
once including delisted trusts, once excluding them.

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
- Beat rate at 4 horizons times 2 survivorship treatments.
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
  output and sorts naturally. **Now spans 1967-12 to the current month (~710 rows), not the
  181 the CSV implied** — SPY reaches back to 1993 and 75 trusts to 2011 or earlier.
- **`fact_monthly_performance`** — one row per (ticker, month). Carries the **versioned**
  `ticker_key`, resolved once at build time, so "returns while managed by X" is a plain
  join with no date-range condition to forget.
- **`fact_horizon_performance`** — one row per (ticker, horizon). `total_return`,
  `annualised_return`, `index_return_same_period`, `beat_index`.

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
| 2 | **Bronze** — all-STRING recast | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | **EDA** — evidence for Silver's rules | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | **Silver** — scale repair, currency, total return | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 5 | **Gold dims** — `dim_date`, `dim_ticker` SCD2 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 6 | **Gold facts** — monthly plus horizon | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 7 | **Semantic plus dashboard** | ⬜ | ⏸️ | ⏸️ | ⬜ | ⬜ |
| 8 | **Orchestration** — one monthly Workflow | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 9 | **Presentation** — README, video, LinkedIn | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

### Open at this moment

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

**Step 4 — Silver**
Eight rules, each citing evidence from step 3: scale repair (the hardest — 36 symbols, 743
corrupted rows), currency normalisation, stub rejection, the `PCFT` zero, partial-month
exclusion, the month key, **total return via `LAG`** —
`(Close_t + Dividends_t) / Close_{t-1} - 1`, compounded — applied identically to trusts and
to SPY, then the union with the two archived delisted trusts. MERGE on the business key.
Flat tables, no SCD2 here.

**Step 5 — Gold dimensions**
`dim_date` (~710 rows, 1967-12 onward) and `dim_ticker` with the SCD2 MERGE closing and
opening version rows.

**Step 6 — Gold facts**
`fact_monthly_performance`, then `fact_horizon_performance` with the 36-month minimum and
delisted trusts judged over their own lifespan against the index over that same span.

**Step 7 — Semantic and dashboard**
Scope deliberately parked until Gold is real. Candidates: beat-rate summary (the headline),
growth curves, trust leaderboard, beat rate by sector.

**Step 8 — Orchestration**
One Databricks Workflow, chained tasks, monthly schedule. Not theatre: the SPY side
genuinely gains a month per run.

**Step 9 — Presentation**
README (architecture diagram, how to run, results), 5–10 minute video, LinkedIn post.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| **yfinance is now a single point of failure.** It is an unofficial scraper and both sides of the comparison depend on it | The biggest risk in the project since 2026-09-19. Landing OVERWRITEs per run, so a bad pull replaces a good one. Mitigation: the pull log makes a degraded run obvious at a glance, and the verification cells assert exact symbol counts rather than "it ran" |
| **The scale repair is the hardest piece.** 36 of 96 trusts carry mis-scaled rows inside the window, 743 in total, and the factor differs by ticker — CGT a clean 10x, CLDN roughly 1400x | Detect per row against the median of neighbouring months, derive the ratio, rescale. Step 3 must prove the detection works before step 4 relies on it. Excluding the affected trusts instead would discard 37% of the sample |
| **The total-return calculation is the number everything rests on** | One formula, applied identically to trusts and SPY so any error cancels on both sides. Sanity-check against a known case: HFEL, 10 years, price return −25.8% against total return +39.0% |
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
| Why not use Yahoo's `Adj_Close`? | It is dividend-adjusted for SPY but not for UK trusts — 97 of 102 show an adjustment under 0.5%, including HFEL, which paid 232.6p on a 359p share. Using it would understate the trusts. |
| How do you know delisted trusts are missing? | The pipeline records it. `landing.yf_pull_log_raw` holds a row per requested symbol, and 18 trusts return nothing — 16 with `No data found, symbol may be delisted`, 2 with an empty frame. |
| What would you do with more time? | Source real manager history so the SCD2 has depth on day one, and find a source for the delisted trusts so survivorship rests on more than two. |
