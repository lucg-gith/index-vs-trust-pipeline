# Presentation prep

Everything needed for the 5–10 minute defence, in the order the brief asks for it.
**Results sections are marked TO FILL IN** — they get completed once Gold runs.

**Last updated:** 2026-09-18

> Written in English as our working language. If the defence is in Spanish, say so and this
> gets translated — the section headings below already mirror the brief's Spanish structure.

---

## The 30-second version

> I built a five-layer data pipeline on Databricks to answer one question: **what percentage
> of UK investment trusts actually beat the S&P 500?** Not which one won — the *share* that
> beat it. I report it at four time horizons, and twice at each one: including and excluding
> trusts that died along the way. That second number is the point — most comparisons quietly
> drop the failures, which flatters the industry. The gap between my two numbers *is* that
> bias, measured rather than disclaimed.

Memorise this. It is the answer to "so what did you build?" and it opens the talk.

---

## 1. Problema — 1 minute

**The question:** what % of UK investment trusts beat the S&P 500?

**Define the beat rate out loud, because nobody knows the term:**
> "The beat rate is the share of trusts that outperformed the index over a given window. If
> 31 of 102 trusts beat it over ten years, the beat rate is 30%."

**Why it matters:** UK investors are sold actively-managed trusts on the promise of beating
the market. This measures whether that promise holds, at scale, over 15 years.

**The twist that makes it yours — survivorship bias.** Say this explicitly:
> "Funds that collapse stop being counted. If you measure only the survivors, the industry
> looks better than it was. So I report every horizon twice — once with the delisted trusts,
> once without. The gap between those two numbers is the bias, as a number."

---

## 2. Arquitectura — 2 minutes

### Data sources — three of them

| # | Source | Gives | Arrives as |
|---|---|---|---|
| 1 | **`yfinance`** (Yahoo Finance) | SPY, IVV, VOO, SPLG — the index side | Live API pull, **daily** |
| 2 | **`uk_investment_trusts.csv`** | Trust metadata: name, ticker, AIC sector, **manager**, **management group** | Committed CSV, 120 rows |
| 3 | **`uk_investment_trusts_price_history_monthly.csv`** | Trust prices — the trust side | Committed CSV, 16,357 rows, **monthly** |

Two points to make about this mix:

- **The grains differ.** yfinance is daily, the trust data is monthly. Silver collapses SPY
  to the last trading day of each month so both sides meet at the same `month_key`.
- **Only yfinance has dividends.** The trust data is price-only. So returns are **price
  return on both sides**, using SPY's `Close` and never `Adj_Close`. *Say this before anyone
  asks* — see "Limitations" below.

A fourth file, `trust_universe_seed.csv`, is deliberately unused: same tickers, and its
`is_active` column contradicted the price data. Listing status is derived from the prices
instead — active while still priced. **Evidence beats assertion.**

### The five layers

| Layer | Job | Write strategy |
|---|---|---|
| **Landing** | exactly as it arrived, no transformation at all | OVERWRITE |
| **Bronze** | same rows, every column STRING, nothing rejected | OVERWRITE |
| **Silver** | *all* quality work — month keys, scale repair, returns | MERGE |
| **Gold** | the dimensional model, SCD2 via MERGE | MERGE |
| **Semantic** | thin views feeding the dashboard | views |

**The line that explains the whole design:** *"Landing and Bronze are not allowed to fix
anything. If a row is wrong, it lands wrong — so that when Silver repairs it, the repair is
auditable against the original."*

### The star schema

```
dim_date  ──────────┐
                    ├──►  fact_monthly_performance
dim_ticker (SCD2) ──┤     fact_horizon_performance
                    ┘
```

Two dimensions, two facts. **Both dims join directly to both facts — it is a true star, not
a snowflake.** Trusts and SPY live in the same dimension, so trust-vs-index is a self-join
on one table rather than a union.

### Tech stack

Databricks (Free Edition) · Unity Catalog · Delta Lake · Spark SQL · Databricks Workflows ·
Python + `yfinance` for ingestion · Git / GitHub

---

## 3. Demo en vivo — 3 minutes

**Rehearse this. Have the tabs open before you start. Do not improvise.**

### Beat #1 — the repo (20 sec)
Show the layer-first folder structure: `00_landing`, `01_bronze`, `02_silver`, `03_gold`,
`04_semantic`, `05_orchestration`. Say: *"the folders are the architecture."*

### Beat #2 — the Workflow (40 sec)
Show the Databricks Workflow with its chained tasks and monthly schedule. Say: *"one
Workflow, tasks chained in layer order, scheduled monthly — and monthly is not decorative,
the index side genuinely gains a month of data every run."*

### Beat #3 — bad data surviving, then being fixed (60 sec)
This proves the layer separation is real, not just folder names.

```sql
-- Bronze: the defect is still there, untouched
SELECT ticker, `date`, price_gbx_or_gbp
FROM `index-vs-trust-pipeline`.bronze.trust_prices
WHERE ticker = 'PCFT' AND `date` = '2019-11-01';     -- 0.000

-- Silver: same row, now handled
SELECT * FROM `index-vs-trust-pipeline`.silver.trust_prices
WHERE ticker = 'PCFT' AND month_key = 201911;
```

Say: *"Bronze is not allowed to clean. Silver is where every rule lives, and because Bronze
kept the original, I can prove what I changed."*

### Beat #4 — SCD Type 2, live (60 sec) ← **the money shot**
Nobody else will do this live.

1. Show `dim_ticker` for one trust — **one row**, `is_current = true`.
2. Edit the manager name in `data/uk_investment_trusts.csv`.
3. Re-run the pipeline task.
4. Same query — **two rows now**: the old one closed with an end date and `is_current =
   false`, the new one open.

Say: *"That is Slowly Changing Dimension Type 2. When a trust's manager, management group or
listing status changes, I close the old version row and open a new one — so history is kept,
not overwritten."*

### Beat #5 — the dashboard (20 sec)
Land on the beat-rate headline. Read the two numbers aloud — with and without delisted
trusts — and name the gap.

---

## 4. Resultados — 2 minutes

### ⚠️ TO FILL IN once Gold runs

| Horizon | Beat rate (survivors only) | Beat rate (incl. delisted) | Survivorship bias gap |
|---|---|---|---|
| 15 years | _TBD_ | _TBD_ | _TBD_ |
| 10 years | _TBD_ | _TBD_ | _TBD_ |
| 5 years | _TBD_ | _TBD_ | _TBD_ |
| 3 years | _TBD_ | _TBD_ | _TBD_ |

Also to fill in: best and worst performing trusts · does any management group consistently
beat the index · **do solo-managed trusts beat the index more often than team-managed ones**
(this one is free — it comes from the `manager_structure` column, and nobody else will have it).

### Learnings to say out loud

These matter as much as the numbers — the brief explicitly grades reasoning.

- **"The data told me my design was wrong."** The first design versioned the SCD2 on a
  computed top-20 rank band. Then a manager file appeared and I dropped that entirely —
  manager history is a real business event, and it removed the single most complex piece of
  the pipeline.
- **"I checked what the platform already gives you."** I nearly added lineage columns to
  Bronze, then found Delta's `DESCRIBE HISTORY` already records load time, user and notebook,
  and Unity Catalog draws lineage automatically. With OVERWRITE, a per-row timestamp would
  repeat one identical value across 16,357 rows. So I left it out.
- **"Not every attribute deserves a dimension."** 227 managers, but 224 of them run exactly
  one trust — a `dim_manager` would have been a column in disguise, and many-to-many on top.
  Management group *is* shared (J.P. Morgan runs 12 trusts), so that one earned its place as
  a real grouping.

---

## 5. Preguntas — the defence bank

The brief lists five questions it expects. All five, plus the ones this design invites:

| Question | Answer |
|---|---|
| **¿Por qué elegiste ese modelo dimensional?** | Two dims, two facts, every dimension joins straight to the fact — a true star. Trusts and the index sit in one dimension, so comparing them is a self-join instead of a union. |
| **¿Qué pasa si la fuente cambia de schema?** | Bronze lists every column explicitly rather than `SELECT *`, so a new or missing column surfaces as an error, not a silent change. The index notebook also compares the live column list against the expected one before it builds. |
| **¿Cómo garantizás que no se duplican datos?** | OVERWRITE into Landing and Bronze, MERGE on the business key into Silver and Gold. Re-running changes no row counts. |
| **¿Qué harías diferente con más tiempo?** | Source real manager history so the SCD2 has depth on day one instead of accruing forward, and get dividend data so I could compare total returns rather than price returns. |
| **¿Cómo escalarías a 10x más datos?** | Partition the facts by year, and switch Landing and Bronze from full OVERWRITE to incremental loads with Auto Loader. Silver and Gold already MERGE, so they scale as-is. |
| **Why a Landing *and* a Bronze?** | Landing is a transient receiving zone holding exactly what arrived. Bronze is the permanent record under one uniform all-STRING contract. Different jobs, different lifespans. |
| **Show me your SCD2** | Demo beat #4 — change a manager, re-run, two rows. |
| **Why is `month_key` not a hash like the other keys?** | It is a plain `YYYYMM` integer. It is readable in query output and sorts chronologically for free — a hash would give up both for no benefit. |
| **Why price return and not total return?** | The trust data has no dividend column, so I discard the index's dividends too. Comparing a dividend-inclusive index against price-only trusts would be rigged against the trusts. |
| **Why keep trusts that fail your minimum history?** | They stay in the dimension so the universe stays honest, but they produce no fact rows and count in no denominator. |

**If you do not know an answer, say so.** The brief says this directly: *"No tengas miedo de
decir 'no sé'. Lo que importa es tu razonamiento."*

---

## Limitations — say these before you are asked

Volunteering a weakness reads as rigour. Being caught hiding one does the opposite.

1. **Price return, not total return.** Dividends are excluded on *both* sides, because the
   trust data has none. This understates both, and trusts slightly more, since UK investment
   trusts are typically income-oriented.
2. **The SCD2 has no history on day one.** The manager file is a current snapshot, so every
   trust starts as version 1 and history accrues from the next run. That is exactly how it
   would behave in production against a live source.
3. **The 15-year window starts in 2011,** so it excludes the 2008 financial crisis. It does
   include COVID (March 2020), the 2022 bear market and August 2024.
4. **~25 tickers arrived on an inconsistent scale** and were repaired, not deleted. The
   repair rule is documented in the EDA notebook with the evidence behind it.

---

## Key numbers to have memorised

| | |
|---|---|
| Trusts with price history | **102** |
| Monthly price rows | **16,357** |
| Months covered | **181** (2011-09 → 2026-09) |
| Trusts in the metadata file | **120** rows, **118** tickers |
| Management groups | **52** — J.P. Morgan runs 12, Baillie Gifford 10 |
| Individual managers | **227** — only **3** run more than one trust |
| Trusts with 2+ managers | **70 of 97** (max 12 on one trust) |
| Pipeline layers | **5** |
| Gold tables | **4** — 2 dimensions, 2 facts |
| Horizons reported | **4**, each twice = **8** headline numbers |
| Trusts that stopped early | **1** (BCPT, last priced 2024-11) |

---

## Deliverables checklist

- [ ] Pipeline runs end-to-end on a schedule
- [ ] README — one-line what, architecture diagram, tech list, how to run, results
- [ ] Dashboard screenshots
- [ ] 5–10 minute video, with voice (Loom, OBS, or a phone)
- [ ] LinkedIn post — hook, what you built, what you learned, repo + video link
- [ ] LinkedIn profile updated: "Data Engineer" headline, about section, photo
- [ ] Results filled into section 4 of this document

### The personal angle

The brief is explicit that the background is an advantage, not a gap to apologise for:
*"Un ex-contador entiende el negocio. Un ex-docente comunica mejor."* Career-changing into
data from a non-technical field means you chose a question you actually care about and can
explain to a non-technical audience — which is exactly what the beat rate is.
