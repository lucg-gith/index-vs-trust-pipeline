# Rebuilding this dashboard in Power BI Desktop

The live dashboard is a Databricks AI/BI dashboard, defined in `beat_rate.lvdash.json` next
to this file. This sheet reproduces the same page in Power BI against the same views, so the
two always show the same numbers.

Nothing here is design work. Every tile is a view, a chart type and two or three fields.

---

## 1. Connect

**Get Data → Azure Databricks**, then:

| Field | Where to find it |
|---|---|
| Server hostname | SQL Warehouses → your warehouse → **Connection details** |
| HTTP path | same panel |
| Data Connectivity mode | **Import** |
| Catalog / Database | `index-vs-trust-pipeline` / `semantic` |

**Import, not DirectQuery.** The largest view used here is 445 rows. Import makes the report
open instantly, survives the warehouse auto-stopping after 10 minutes, and still refreshes
on demand. DirectQuery would wake the warehouse on every click for no benefit.

Take only the two views the page needs: **`v_beat_rate`** and **`v_leaderboard`**. Load them
as separate tables; no relationship between them is required, because no visual crosses the
two.

---

## 2. The horizon slicer

Power BI has no dashboard parameter, so the equivalent is a **slicer** on
`v_beat_rate[horizon_years]`, set to **single select**, default **15**.

Then, so it drives only the tiles it should:

- Tiles 1–3, 5 and 7 → **slicer applies**
- Tiles 4 and 6 → **Format → Edit interactions → set the slicer's interaction to `None`**

Tiles 4 and 6 exist to show all five horizons at once. If the slicer reached them they would
collapse to a single bar. This is the one piece of wiring that is easy to get wrong.

The slicer sits on `v_beat_rate`, so to make it reach `v_leaderboard` (tiles 5 and 7) either
add a small `horizons` table related to both, or place a second synced slicer on
`v_leaderboard[horizon_years]` and sync them via **View → Sync slicers**. The synced-slicer
route is simpler and needs no model changes.

---

## 3. The tiles

| # | Tile | Visual | Table | Fields | Expected at 15 years |
|---|---|---|---|---|---|
| 1 | Beat the S&P 500 | Card | `v_beat_rate` | `beat_rate_pct` (Max) | **5.3** |
| 2 | Beat it AND were less volatile | Card | `v_beat_rate` | `beat_and_calmer_pct` (Max) | **0.0** |
| 3 | Annualised volatility | Multi-row card | `v_beat_rate` | `median_volatility_pct`, `index_volatility_pct` (both Max) | **24.2** and **14.2** |
| 4 | Beat rate by horizon | Clustered bar | `v_beat_rate` | Axis `horizon_years`, Value `beat_rate_pct` (Max) | 5.3 · 10.6 · 15.6 · 30.0 · 41.6 |
| 5 | Risk against reward | Scatter | `v_leaderboard` | X `volatility_pct` (Max), Y `annualised_return_pct` (Max), Legend `entity_type`, Details `ticker` | 76 trust points, 3 tracker points |
| 6 | Survivorship | Clustered bar | `v_beat_rate` | Axis `horizon_years`, Legend `cohort`, Value `beat_rate_pct` (Max) | two near-identical series |
| 7 | Who ran the winners | Table | `v_leaderboard` | `rank_by_return`, `ticker`, `name`, `manager`, `management_group`, `annualised_return_pct`, `volatility_pct` | ATT, JEGI, SMT, JAM, PHI … |

**Filters every tile needs:**

- Tiles 1–4: `cohort = "all trusts"`. The headline is never the survivors-only number.
- Tile 6: no cohort filter — showing both is the entire point of the tile.
- Tile 5: none. SPY must stay on the chart as the reference point.
- Tile 7: `entity_type = "Trust"`, Top N = 10 by `rank_by_return` ascending. The trackers are
  excluded because `dim_ticker` stores their manager as the literal `NotApplicable`, and
  because an index having no manager is the point of the comparison rather than a cell value.

**Details on the scatter matter.** Without `ticker` in the Details well, Power BI aggregates
every trust into one point. This is the single most common way to get this visual wrong.

---

## 4. The measures AI/BI gets for free

Only two, both in `v_leaderboard` unless noted.

```dax
-- The "4 of 76 trusts" subtitle under tile 1. Lives on v_beat_rate.
Beat count of total =
    FORMAT( MAX( v_beat_rate[beat_count] ), "0" ) & " of " &
    FORMAT( MAX( v_beat_rate[trusts] ),     "0" ) & " trusts"

-- The scatter's crosshair. Analytics pane -> X-Axis Constant Line and
-- Y-Axis Constant Line, each set to "Field value" and pointed at these.
SPY volatility =
    CALCULATE( MAX( v_leaderboard[volatility_pct] ),
               v_leaderboard[ticker] = "SPY" )

SPY annualised return =
    CALCULATE( MAX( v_leaderboard[annualised_return_pct] ),
               v_leaderboard[ticker] = "SPY" )
```

The two constant lines cut the scatter into the four quadrants the study is built around.
The one above and to the left — higher return at lower risk than the index — is **empty at
15 and 10 years**. At 5 years one trust reaches it, and at 1 year three do. Do not label it
"empty" on the tile, because the slicer can make that false.

---

## 5. Check it matches

Set the slicer to 15 years and confirm: **5.3**, **0.0**, **24.2 vs 14.2**, bars reading
5.3 / 10.6 / 15.6 / 30.0 / 41.6, and ATT top of the table at 24.91% with 30.1% volatility.

If any of those disagree with the AI/BI dashboard, the cause is almost always a missing
`cohort = "all trusts"` filter or a scatter without `ticker` in Details.
