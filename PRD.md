# PRD — Do UK investment trusts beat the S&P 500?

**Last updated:** 2026-09-18
**Current position:** Step 3 of 9 — EDA. Steps 1–2 are written but **not yet verified on Databricks**.

---

## 1. The question

> **What percentage of UK investment trusts actually beat the S&P 500?**

Not "which one won" — the **beat rate**: the share of trusts that outperformed the index
over a given window. If 31 of 102 trusts beat it over 10 years, the beat rate is 30%.

Reported at **four horizons — 15, 10, 5 and 3 years** — and **twice at each horizon**:
once including delisted trusts, once excluding them.

### Why report it twice

Funds that collapse stop being counted. Measure only the survivors and the industry looks
better than it was — **survivorship bias**. Most published comparisons simply disclaim it.
Reporting both numbers turns the bias into a measured quantity: the gap between the two
*is* the bias, in percentage points.

This is the project's main analytical claim, and the main thing to defend.

---

## 2. Success criteria

### The assignment

| Rubric level | Requirement | Status |
|---|---|---|
| **Mínimo** | Bronze → Silver → Gold, at least 2 tables | on track |
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
- **Time is the scarcest resource.** The brief says it outright: *"No intentes hacer todo.
  Es mejor un pipeline simple bien hecho que uno complejo a medias."*
- The employer is **never named** anywhere in the repo, commits or deliverables.

---

## 3. Scope

### In

- 102 UK investment trusts with monthly price history, 2011-09 to 2026-09.
- The S&P 500 via SPY, with IVV/VOO/SPLG as a secondary credibility check.
- Beat rate at 4 horizons times 2 survivorship treatments.
- SCD2 history on trust manager, management group and listing status.

### Out, and why

| Excluded | Reason |
|---|---|
| S&P 500 constituent-level modelling | SPY already publishes the index; modelling 500 stocks adds no answer |
| Dividend-inclusive returns | The trust data has no dividend column. Price return on both sides is the only fair comparison |
| A top-20 filter on the fact table | Filtering to the best performers before asking "what % beat the index" is circular |
| `rank_band` SCD2 | Existed only because no manager data was available. Manager history replaces it at a fraction of the complexity |
| `dim_manager` as a table | 224 of 227 managers run exactly one trust — the dimension would be a column in disguise, and it is many-to-many |

---

## 4. Data

Three sources. Facts below were verified directly against the files, not assumed.

### `data/uk_investment_trusts.csv` — metadata

120 rows, 118 unique tickers. Trust name, ticker, AIC sector, **manager**,
**management_group**, notes.

- 97 of the 102 priced tickers have a manager. 227 distinct people; **only 3 manage more
  than one trust**. 70 trusts have 2 or more managers (max 12).
- **52 management groups**, heavily shared — J.P. Morgan runs 12 trusts, Baillie Gifford 10.
- **It is a snapshot, not history.** No start/end dates. Run 1 makes everything version 1.

### `data/uk_investment_trusts_price_history_monthly.csv` — prices

16,357 rows, 102 tickers, 2011-09-30 to 2026-09-17. **Price only, no dividends.**

Known defects, all of which must reach Silver intact:

- Date labels mix month-end and next-month-first (Dec 31 appears as Jan 1). **Rule: if
  `day <= 3`, the row belongs to the previous month.** Verified: 0 collisions, 181 months.
- **~25 tickers carry interleaved rows on a wrong scale**, and the factor *drifts within* a
  ticker — CGT ~10x, FCIT ~4.0–4.7x, CLDN ~1180–1490x. **No single global fix exists.**
- One zero price: `PCFT`, 2019-11-01.
- 145 rows below 1.0 — the USD/EUR-quoted trusts. **Not errors.**
- **Only one trust stops early: BCPT, last priced 2024-11.**

### Yahoo Finance via `yfinance` — the index

SPY, IVV, VOO, SPLG. Daily. Has dividends and adjusted close, both deliberately unused.

### Superseded

`trust_universe_seed.csv` — same 118 tickers, and its only extra column (`is_active`)
contradicted the price data: it claimed 17 inactive, but 13 have no prices at all and CSH
is flagged inactive while still priced through 2026-09. **Status is derived from the prices
instead** — active while still priced. Evidence beats assertion.

---

## 5. Architecture

Catalog `` `index-vs-trust-pipeline` `` — the hyphens mean **backticks on every SQL
reference**. Five schemas.

| Layer | Job | Write | Defends |
|---|---|---|---|
| **Landing** | data exactly as it arrived; no transformation at all | OVERWRITE | "what did the source actually send?" |
| **Bronze** | same rows, every column STRING, nothing rejected | OVERWRITE | one uniform contract for Silver |
| **Silver** | *all* quality work — month keys, scale repair, returns | MERGE | "how do you handle bad data?" |
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
- **`dim_date`** — monthly, 181 rows. `month_key` is a plain `YYYYMM` INT, not a hash:
  readable in output and sorts naturally.
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
| 1 | **Landing** — 3 ingests plus schema | ✅ | ✅ | ✅ | ✅ | ⬜ |
| 2 | **Bronze** — all-STRING recast | ✅ | ✅ | ✅ | ✅ | ⬜ |
| 3 | **EDA** — evidence for Silver's rules | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| 4 | **Silver** — cleaning, repair, returns | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 5 | **Gold dims** — `dim_date`, `dim_ticker` SCD2 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 6 | **Gold facts** — monthly plus horizon | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 7 | **Semantic plus dashboard** | ⬜ | ⏸️ | ⏸️ | ⬜ | ⬜ |
| 8 | **Orchestration** — one monthly Workflow | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 9 | **Presentation** — README, video, LinkedIn | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

### Open at this moment

- **Steps 1 and 2 have never been run on Databricks.** They are written and their expected
  numbers are checked against the source files, but no Delta table exists yet. Verification
  means a real execution, not a code review.
- **The Databricks Git folder must be re-cloned** — a history rewrite on 2026-09-18 changed
  every commit hash.

### Step detail

**Step 3 — EDA** *(next)*
Profile Bronze and produce the documented evidence behind every Silver rule. Specifically:
prove the `day <= 3` month rule produces 0 collisions; characterise the ~25 mis-scaled
tickers and show the factor drifts within a ticker; confirm the sub-1.0 prices are
currency-quoted and not errors; find anything not yet known. Output is a notebook in
`01_bronze/eda/`. **This is what makes the scale repair defensible rather than arbitrary.**

**Step 4 — Silver**
Month keys on both sides, the per-row scale repair, monthly returns via `LAG`, MERGE on the
business key. Flat tables — no SCD2 here. Every rule cites step 3.

**Step 5 — Gold dimensions**
`dim_date` (181 rows) and `dim_ticker` with the SCD2 MERGE closing and opening version rows.

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
| **The scale repair is the hardest piece.** The factor drifts within a ticker, so no global constant works | Detect per row against the median of neighbouring months, derive the ratio, rescale. Step 3 must prove the detection works before step 4 relies on it |
| **SCD2 has no history on run 1** — the source is a snapshot | Expected and explained. Demo it live by changing a manager and re-running |
| yfinance is an unofficial scraper and can break | Only the index side depends on it. Trust data is a committed CSV |
| Time runs out before step 9 | Steps 1–6 clear "Ideal" on their own. Dashboard and video are bonus — cut from the end, not the middle |
| 5 trusts have no manager (ADIG, BCPT, BSIF, CSH, EOT) | They stay in `dim_ticker` with a null manager. Not dropped — the universe stays honest |

---

## 9. Deliverables checklist

- [ ] Pipeline running end-to-end on a schedule
- [ ] README: one-line what, architecture diagram, tech list, how to run, results
- [ ] Dashboard screenshots
- [ ] 5–10 minute video with voice
- [ ] LinkedIn post linking repo and video
- [ ] **Stated openly in the README:** returns are price-only on both sides, because the
      trust data has no dividends. SPY's `Close`, never `Adj_Close`

---

## 10. Defence — one sentence each

| Question | Answer |
|---|---|
| Why this dimensional model? | One fact, two dims, every dim joins straight to the fact. Trust vs index is a self-join on one table. |
| How do you guarantee no duplicates? | OVERWRITE into Landing and Bronze, MERGE on the business key into Silver and Gold. |
| Show me your SCD2 | A trust's manager, firm or listing status changes and I close the old row and open a new one — watch, I'll change one and re-run. |
| What if the source changes schema? | Bronze lists every column explicitly, so a new or missing column is an error, not a silent change. |
| Why is there a Landing *and* a Bronze? | Landing is a transient receiving zone holding exactly what arrived; Bronze is the permanent record under one all-STRING contract. |
| Why no lineage columns? | Delta's `DESCRIBE HISTORY` already records load time, user and notebook, and UC draws lineage. With OVERWRITE, a per-row stamp would repeat one value across every row. |
| What would you do with more time? | Source real manager history so the SCD2 has depth on day one, and add dividend data to compare total returns. |
